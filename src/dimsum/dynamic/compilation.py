import time
import dataclasses
import logging
import functools
import ast
import jsonpickle
import sys
import inspect
import typing as imported_typing
from collections import ChainMap
from typing import List, Dict, Any, Optional, Callable, Union

from loggers import get_logger
from model import (
    Entity,
    World,
    Scope,  # globals
    StandardEvent,  # globals
    Event,
    Common,  # globals
    Success,  # globals
    Failure,  # globals
    context,
    get_all_events,  # globals
    All,
    Action,
    Unknown,
    AlwaysTrue,
    ArgumentTransformer,
)
import tools
import grammars

from .core import (
    EntityAndBehavior,
    EntityBehavior,
    Dynsum,
    Cron,
    Held,
    Ground,
    CronEvent,
    LibraryBehavior,
    Registered,
    Receive,
)
from .calls import DynamicCall
from .dynpost import DynamicPostService, DynamicPostMessage
from .language import SimplifiedTransformer
from .ldc import log_dynamic_call

# TODO globals
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.movement as movement
import scopes.inbox as inbox

log = get_logger("dimsum.dynamic")
errors_log = get_logger("dimsum.dynamic.errors")


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


def flatten(l):
    return [item for sl in l for item in sl]
