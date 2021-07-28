import ast
import sys
import abc
import traceback
import logging
import copy
import dataclasses
import functools
import inspect
import jsonpickle
import time
import contextvars
import typing as imported_typing
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
from collections import ChainMap

import grammars
import transformers
import saying
import domains as session  # TODO circular
import serializing
import finders
import tools
from loggers import get_logger
from model import (
    Entity,
    Scope,
    World,
    Ctx,
    Event,
    Common,
    StandardEvent,
    Reply,
    Action,
    Success,
    Failure,
    get_all_events,
    DynamicFailure,
    Unknown,
    ManagedHooks,
    context,
    Condition,
    AlwaysTrue,
    All,
    ArgumentTransformer,
    ItemFinder,
)
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.movement as movement
import scopes.inbox as inbox

log = get_logger("dimsum.dynamic")
errors_log = get_logger("dimsum.dynamic.errors")
active_behavior: contextvars.ContextVar = contextvars.ContextVar(
    "dimsum:behavior", default=None
)


class LibraryBehavior:
    @abc.abstractmethod
    async def create(self, ds: "Dynsum"):
        raise NotImplementedError


class Dynsum:
    @abc.abstractmethod
    def language(self, prose: str, condition=None):
        raise NotImplementedError

    @abc.abstractmethod
    def cron(self, spec: str):
        raise NotImplementedError

    @abc.abstractmethod
    def received(self, hook: Union[type, str], condition=None):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def hooks(self) -> All:
        return All()

    @abc.abstractmethod
    def behaviors(self, behaviors: List[LibraryBehavior]):
        raise NotImplementedError

    @abc.abstractmethod
    def evaluators(self, evaluators: List[grammars.CommandEvaluator]):
        raise NotImplementedError


class NoopDynsum(Dynsum):
    def language(self, prose: str, condition=None):
        pass

    def cron(self, spec: str):
        pass

    def received(self, hook: Union[type, str], condition=None):
        pass

    def behaviors(self, behaviors: List[LibraryBehavior]):
        pass

    def evaluators(self, evaluators: List[grammars.CommandEvaluator]):
        pass

    @property
    def hooks(self) -> All:
        return All()


@dataclasses.dataclass
class DynamicCall:
    entity_key: str
    behavior_key: str
    name: str
    time: float
    elapsed: float
    logs: List[str]
    exceptions: Optional[List[Dict[str, Any]]]
    context: Dict[str, Any] = dataclasses.field(repr=False, default_factory=dict)


@dataclasses.dataclass
class Held(Condition):
    entity_key: str

    def applies(self) -> bool:
        entity = context.get().find_by_key(self.entity_key)
        assert entity
        return tools.in_pockets(entity)


@dataclasses.dataclass
class Ground(Condition):
    entity_key: str

    def applies(self) -> bool:
        entity = context.get().find_by_key(self.entity_key)
        assert entity
        return tools.on_ground(entity)


@dataclasses.dataclass(frozen=True)
class Registered:
    prose: str
    handler: Callable = dataclasses.field(repr=False)
    condition: Condition


@dataclasses.dataclass(frozen=True)
class Receive:
    hook: str
    handler: Callable = dataclasses.field(repr=False)
    condition: Condition


@dataclasses.dataclass(frozen=True)
class CronKey:
    entity_key: str
    spec: str


@dataclasses.dataclass(frozen=True)
class Cron:
    entity_key: str
    spec: str
    handler: Callable = dataclasses.field(repr=False)

    def key(self) -> CronKey:
        return CronKey(self.entity_key, self.spec)


@dataclasses.dataclass(frozen=True)
class CronEvent(Event):
    entity_key: str
    spec: str


@dataclasses.dataclass
class DynamicPostMessage(inbox.PostMessage):
    message: inbox.PostMessage


@dataclasses.dataclass
class DynamicPostService:
    postService: inbox.PostService

    async def future(
        self, receiver: Entity, when: datetime, message: inbox.PostMessage
    ):
        return await self.postService.future(
            receiver, when, DynamicPostMessage(message)
        )


class EntityBehavior(grammars.CommandEvaluator):
    @property
    def hooks(self):
        return All()  # empty hooks

    @property
    def crons(self) -> List[Cron]:
        return []

    async def notify(self, ev: Event, **kwargs):
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class SimplifiedAction(Action):
    entity: Entity
    registered: Registered
    args: List[Any]

    def _transform_reply(self, r: Union[Reply, str]) -> Reply:
        if isinstance(r, str):
            return Success(r)
        return r

    async def _transform_arg(
        self, arg: ItemFinder, world: World, person: Entity, ctx: Ctx
    ) -> Optional[Entity]:
        assert isinstance(arg, ItemFinder)
        return await ctx.apply_item_finder(person, arg)

    async def _args(self, world: World, person: Entity, ctx: Ctx) -> List[Any]:
        return [await self._transform_arg(a, world, person, ctx) for a in self.args]

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        try:
            args = await self._args(world, person, ctx)
            reply = await self.registered.handler(
                *args,
                this=self.entity,
                person=person,
                **kwargs,
            )
            if reply:
                return self._transform_reply(reply)
            return Failure("no reply from handler?")
        except Exception as e:
            errors_log.exception("handler:error", exc_info=True)
            return DynamicFailure(str(e), str(self.registered.handler))


@dataclasses.dataclass
class SimplifiedTransformer(transformers.Base):
    registered: Registered
    entity: Entity

    def start(self, args):
        return SimplifiedAction(self.entity, self.registered, args)


@dataclasses.dataclass
class CompiledEntityBehavior(EntityBehavior, Dynsum):
    entity_key: str
    entity_hooks: All
    wrapper_factory: Callable = dataclasses.field(repr=False)
    registered: List[Registered] = dataclasses.field(default_factory=list)
    receives: List[Receive] = dataclasses.field(default_factory=list)
    scheduled_crons: List[Cron] = dataclasses.field(default_factory=list)
    evaluator_override: Optional[grammars.CommandEvaluator] = None
    declarations: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def language(self, prose: str, condition=None):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(
                Registered(
                    prose, self.wrapper_factory(fn), condition=condition or AlwaysTrue()
                )
            )
            return fn

        return wrap

    def cron(self, spec: str):
        def wrap(fn):
            log.info("cron: '%s' %s", spec, fn)
            self.scheduled_crons.append(
                Cron(self.entity_key, spec, self.wrapper_factory(fn))
            )
            return fn

        return wrap

    def received(self, hook: Union[type, str], condition=None):
        def wrap(fn):
            if isinstance(hook, str):
                h = hook
            else:
                h = hook.__name__
            log.info("hook: '%s' %s", h, fn)
            self.receives.append(
                Receive(
                    h, self.wrapper_factory(fn), condition=condition or AlwaysTrue()
                )
            )
            return fn

        return wrap

    @property
    def hooks(self) -> All:
        return self.entity_hooks

    @property
    def crons(self) -> List[Cron]:
        return self.scheduled_crons

    def evaluators(self, evaluators: List[grammars.CommandEvaluator]):
        self.evaluator_override = grammars.PrioritizedEvaluator(evaluators)

    def behaviors(self, behaviors: List[LibraryBehavior]):
        for b in behaviors:
            b.create(self)

    def conditions(self):
        return dict(
            Held=functools.partial(Held, self.entity_key),
            Ground=functools.partial(Ground, self.entity_key),
        )

    async def evaluate(
        self,
        command: str,
        world: Optional[World] = None,
        person: Optional[Entity] = None,
        **kwargs,
    ) -> Optional[Action]:
        assert person

        entity = await context.get().try_materialize_key(self.entity_key)
        assert entity

        log.debug("%s evaluate %s", self, entity)

        for registered in [r for r in self.registered if r.condition.applies()]:

            def transformer_factory(**kwargs):
                assert world and person and entity
                return SimplifiedTransformer(
                    registered=registered,
                    world=world,
                    person=person,
                    entity=entity,
                )

            log.debug("%s evaluate '%s'", self, command)
            log.debug("%s prose=%s", self, registered.prose)

            evaluator = grammars.GrammarEvaluator(
                grammars.DYNAMIC, registered.prose, transformer_factory
            )

            action = await evaluator.evaluate(command)
            if action:
                return action

        if self.evaluator_override is not None:
            action = await self.evaluator_override.evaluate(
                command, world=world, person=person, **kwargs
            )
            if action:
                return action
            return Unknown()

        return None

    def _get_declared_classes(self):
        return [
            value for value in self.declarations.values() if isinstance(value, type)
        ]

    async def notify(self, ev: Event, **kwargs):
        entity = await context.get().try_materialize_key(self.entity_key)
        assert entity

        if isinstance(ev, DynamicPostMessage):
            log.debug("notify: %s", ev)
            log.debug("notify: %s", self.declarations)
            log.info("notify: %s", self._get_declared_classes())
            unpickler = jsonpickle.unpickler.Unpickler()
            decoded = unpickler.restore(
                ev.message, reset=True, classes=list(self._get_declared_classes())
            )
            log.info("notify: %s", decoded)
            return await self.notify(decoded, **kwargs)
        elif isinstance(ev, CronEvent):
            for cron in self.scheduled_crons:
                if ev.spec == cron.spec:
                    try:
                        await cron.handler(this=entity, ev=ev, **kwargs)
                    except:
                        errors_log.exception("notify:exception", exc_info=True)
                        raise
        else:
            for receive in self.receives:
                if ev.name == receive.hook:
                    try:
                        await receive.handler(this=entity, ev=ev, **kwargs)
                    except:
                        errors_log.exception("notify:exception", exc_info=True)
                        raise


@dataclasses.dataclass(frozen=True)
class EntityAndBehavior:
    key: str
    behavior_key: str
    behavior: str


class NoopEntityBehavior(EntityBehavior):
    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        return None

    async def notify(self, ev: Event, **kwargs):
        pass


def _get_default_globals():
    log = get_logger("dimsum.dynamic.user")
    log.setLevel(logging.INFO)  # affects tests, careful
    handler = logging.handlers.MemoryHandler(1024, target=logging.NullHandler())
    log.addHandler(handler)

    # TODO Can we pass an exploded module here?
    event_classes = {k.__name__: k for k in get_all_events()}
    return dict(
        log=log,
        dataclass=dataclasses.dataclass,
        tools=tools,
        Common=Common,
        Entity=Entity,
        Event=StandardEvent,
        PostMessage=inbox.PostMessage,
        Scope=Scope,
        Carryable=carryable.Carryable,
        Exit=movement.Exit,
        fail=Failure,
        ok=Success,
        time=time.time,
        t=imported_typing,
        log_handler=handler,  # private
        **event_classes,
    )


def _get_buffered_logs(frame: Dict[str, Any]) -> List[str]:
    def prepare(lr: logging.LogRecord) -> str:
        return lr.msg % lr.args

    if "log_handler" in frame:
        handler: logging.handlers.MemoryHandler = frame["log_handler"]
        records = [prepare(lr) for lr in handler.buffer]
        handler.flush()
        return records
    return []


class DynamicParameterException(Exception):
    pass


@dataclasses.dataclass
class CustomizeCallArguments(ArgumentTransformer):
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def transform(self, fn: Callable, args: List[Any], kwargs: Dict[str, Any]):
        lookup: ChainMap = ChainMap(kwargs, self.extra)

        def _get_arg(name: str):
            if name in lookup:
                arg = lookup[name]
                if isinstance(arg, inbox.PostService):
                    return DynamicPostService(arg)
                if callable(arg):
                    return arg()
                return arg
            if args:
                return args.pop(0)
            raise DynamicParameterException("'%s' calling '%s'" % (name, fn))

        signature = inspect.signature(fn)
        return [_get_arg(p) for p in signature.parameters]


def log_dynamic_call(
    found: EntityAndBehavior,
    name: str,
    started: float,
    frame: Optional[Dict[str, Any]] = None,
    lokals: Optional[Dict[str, Any]] = None,
    fnargs: Optional[List[Any]] = None,
    fnkw: Optional[Dict[str, Any]] = None,
    exc_info: Optional[bool] = False,
):
    ex: Optional[Dict[str, Any]] = None
    if exc_info:
        ex_type, ex_value, tb = sys.exc_info()
        ex = dict(
            exception=ex_type,
            value=ex_value,
            traceback=traceback.format_exc(),
        )

    finished = time.time()
    logs = _get_buffered_logs(frame) if frame else []
    dc = DynamicCall(
        found.key,
        found.behavior_key,
        name,
        started,
        finished - started,
        context=dict(
            # frame=frame,
            # locals=lokals,
            # fnargs=serializing.serialize(fnargs),
            # fnkw=serializing.serialize(fnkw),
        ),
        logs=logs,
        exceptions=[ex] if ex else None,
    )
    log.debug("dc: %s", dc)
    db = active_behavior.get()
    assert db
    db._record(dc)


@functools.lru_cache
def _compile(found: EntityAndBehavior, compiled_name: str) -> EntityBehavior:
    frame = _get_default_globals()
    started = time.time()

    def load_found() -> Entity:
        return context.get().find_by_key(found.key)

    # TODO dry up?
    def wrapper_factory(fn):
        def create_thunk_locals(args, kwargs) -> Dict[str, Any]:
            assert context.get()
            log.info("thunking: args=%s kwargs=%s", args, kwargs)
            actual_args = CustomizeCallArguments(dict(this=load_found)).transform(
                fn, list(args), {**kwargs, **dict(ctx=context.get())}
            )
            return dict(thunk=(fn, actual_args, {}))

        def sync_thunk(*args, **kwargs):
            lokals = create_thunk_locals(args, kwargs)
            log_dc = functools.partial(
                log_dynamic_call,
                found,
                fn.__name__,
                time.time(),
                frame=frame,
                lokals=lokals,
                fnargs=args,
                fnkw=kwargs,
            )

            def aexec():
                exec(
                    """
# This seems to be an easy clever trick for capturing the global
# during the eval into the method?
def __ex(t=thunk):
    __thunk_ex = None
    try:
        return t[0](*t[1], **t[2])
    except Exception as e:
        __thunk_ex = e
        raise e
""",
                    frame,
                    lokals,
                )

                try:
                    return lokals["__ex"]()
                except:
                    log_dc(exc_info=True)
                    raise

            value = aexec()

            log_dc()

            return value

        async def async_thunk(*args, **kwargs):
            lokals = create_thunk_locals(args, kwargs)
            log_dc = functools.partial(
                log_dynamic_call,
                found,
                fn.__name__,
                time.time(),
                frame=frame,
                lokals=lokals,
                fnargs=args,
                fnkw=kwargs,
            )

            async def aexec():
                exec(
                    """
# This seems to be an easy clever trick for capturing the global
# during the eval into the method?
async def __ex(t=thunk):
    __thunk_ex = None
    try:
        return await t[0](*t[1], **t[2])
    except Exception as e:
        __thunk_ex = e
        raise e
""",
                    frame,
                    lokals,
                )

                try:
                    return await lokals["__ex"]()
                except:
                    log_dc(exc_info=True)
                    raise

            value = await aexec()

            log_dc()

            return value

        if inspect.iscoroutinefunction(fn):
            return async_thunk

        return sync_thunk

    try:
        # Start by compiling the code, if this fails we can bail right
        # away before creating soem of the heavier objects.
        log.info("compiling %s %s", compiled_name, found)
        tree = ast.parse(found.behavior)
        evaluating = compile(tree, filename=compiled_name, mode="exec")

        # This is also assed to the script in the globals as `ds` and
        # exposes the Dynsum interface.
        compiled = CompiledEntityBehavior(
            entity_key=found.key,
            wrapper_factory=wrapper_factory,
            entity_hooks=All(wrapper_factory=wrapper_factory),
        )

        # Wish we could use ChainMap here, instead update globals with
        # the wrapper that's used to remember and direct dynamic
        # calls and with conditonal partials.
        frame.update(**dict(ds=compiled))

        # Also provide partial ctors for a few conditions, local to
        # this entity. This provides Held and Ground, for example.
        frame.update(**compiled.conditions())

        # We squash any declarations left in locals into our
        # globals so they're available in future calls via a
        # rebinding in our thunk factory above. I'm pretty sure
        # this is the only way to get this to behave.
        eval(evaluating, frame, compiled.declarations)

        # Merge local declarations into global frame. This will be all
        # the useful classes and globals the user's module defines.
        frame.update(**compiled.declarations)

        # Return compiled behavior, declarations is used for deserializing.
        return compiled
    except:
        errors_log.exception("dynamic:compile", exc_info=True)
        log_dynamic_call(found, ":compile:", started, frame=frame, exc_info=True)
        raise


class DynamicCallsListener:
    async def save_dynamic_calls_after_success(self, calls: List[DynamicCall]):
        raise NotImplementedError

    async def save_dynamic_calls_after_failure(self, calls: List[DynamicCall]):
        raise NotImplementedError


class LogDynamicCalls(DynamicCallsListener):
    @property
    def log(self):
        return get_logger("dimsum.dynamic.calls")

    def _log_calls(self, calls: List[DynamicCall]):
        for call in calls:
            self.log.info("calls: %s", call)

    async def save_dynamic_calls_after_success(self, calls: List[DynamicCall]):
        self._log_calls(calls)

    async def save_dynamic_calls_after_failure(self, calls: List[DynamicCall]):
        self._log_calls(calls)


@dataclasses.dataclass
class Behavior:
    listener: DynamicCallsListener
    entities: tools.EntitySet
    previous: Optional["Behavior"] = None
    calls: List[DynamicCall] = dataclasses.field(default_factory=list)

    def _get_behaviors(self, e: Entity, c: Entity) -> List[EntityAndBehavior]:
        inherited = self._get_behaviors(e, c.parent) if c.parent else []
        with c.make_and_discard(behavior.Behaviors) as behave:
            b = behave.get_default()

            ignoring = flatten([[b] if b and not b.executable else []])
            if len(ignoring):
                log.warning("unexecutable: %s", ignoring)

            return (
                [EntityAndBehavior(e.key, behavior.DefaultKey, b.python)]
                if b and b.executable and b.python
                else []
            ) + inherited

    @functools.cached_property
    def _behaviors(self) -> Dict[Entity, List[EntityAndBehavior]]:
        return {e: self._get_behaviors(e, e) for e in self.entities.all()}

    def _compile_behavior(
        self, entity: Entity, found: EntityAndBehavior
    ) -> EntityBehavior:
        started = time.time()
        try:
            return _compile(found, compiled_name=f"behavior[{entity}]")
        except:
            log_dynamic_call(found, ":compile:", started, exc_info=True)
            raise

    @functools.cached_property
    def _compiled(self) -> Sequence[EntityBehavior]:
        return flatten(
            [
                [self._compile_behavior(entity, found) for found in all_for_entity]
                for entity, all_for_entity in self._behaviors.items()
            ]
        )

    @property
    def dynamic_hooks(self) -> List["ManagedHooks"]:
        return [c.hooks for c in self._compiled]

    @property
    def evaluators(self) -> Sequence[grammars.CommandEvaluator]:
        return self._compiled

    @property
    def lazy_evaluator(self) -> grammars.CommandEvaluator:
        return grammars.LazyCommandEvaluator(lambda: self.evaluators)

    async def find_crons(self) -> List[Cron]:
        return flatten([c.crons for c in self._compiled])

    async def notify(self, ev: Event, **kwargs):
        for target in [c for c in self._compiled]:
            await target.notify(ev, **kwargs)

    async def verify(self):
        log.info("evaluators: %s", self.evaluators)

    async def __aenter__(self):
        self.previous = active_behavior.get()
        active_behavior.set(self)
        return self

    async def __aexit__(self, type, value, traceback):
        if self.previous:
            for dc in self.calls:
                self.previous._record(dc)
        else:
            if type:
                log.info("exiting: '%s' %s listener=%s", type, value, self.listener)
                if not self.calls:
                    log.warning("dynamic calls empty (exception)")
            if self.calls:
                if type:
                    await self.listener.save_dynamic_calls_after_failure(self.calls)
                else:
                    await self.listener.save_dynamic_calls_after_success(self.calls)

        active_behavior.set(self.previous)
        return False

    def _record(self, dc: DynamicCall):
        self.calls.append(dc)


def log_behavior(entity: Entity, entry: Dict[str, Any], executable=True):
    assert entity
    log.debug("logging %s behavior", entity)
    with entity.make(behavior.Behaviors) as behave:
        # If there's no default behavior then we're here because of
        # inherited behavior.
        b = behave.get_or_create_default()
        assert b
        b.executable = executable
        b.append(entry)
        entity.touch()


def flatten(l):
    return [item for sl in l for item in sl]
