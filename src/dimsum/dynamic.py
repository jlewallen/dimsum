import ast
import dataclasses
import functools
import inspect
import logging
import jsonpickle
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import grammars
import transformers
import saying
import domains as session  # TODO circular
import finders
import tools
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
    ItemFinder,
)
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.inbox as inbox

log = logging.getLogger("dimsum.dynamic")
errors_log = logging.getLogger("dimsum.dynamic.errors")


@dataclasses.dataclass
class Held(Condition):
    entity_key: str

    def applies(self) -> bool:
        entity = session.get().registrar.find_by_key(self.entity_key)
        assert entity
        return tools.in_pockets(entity)


@dataclasses.dataclass
class Ground(Condition):
    entity_key: str

    def applies(self) -> bool:
        entity = session.get().registrar.find_by_key(self.entity_key)
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


@dataclasses.dataclass
class DynamicPostMessage(inbox.PostMessage):
    message: inbox.PostMessage


@dataclasses.dataclass
class DynamicPostService:
    postService: inbox.PostService

    async def future(self, receiver: Entity, when: float, message: inbox.PostMessage):
        return await self.postService.future(
            receiver, when, DynamicPostMessage(message)
        )


class EntityBehavior(grammars.CommandEvaluator):
    @property
    def hooks(self):
        return All()

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
            tools.log_behavior_exception(self.entity)
            return DynamicFailure(str(e), str(self.registered.handler))


@dataclasses.dataclass
class SimplifiedTransformer(transformers.Base):
    registered: Registered
    entity: Entity

    def start(self, args):
        return SimplifiedAction(self.entity, self.registered, args)


@dataclasses.dataclass
class Simplified:
    entity_key: str
    thunk_factory: Callable = dataclasses.field(repr=False)
    registered: List[Registered] = dataclasses.field(default_factory=list)
    receives: List[Receive] = dataclasses.field(default_factory=list)
    hooks: Optional["All"] = dataclasses.field(default_factory=All)

    def language(self, prose: str, condition=None):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(
                Registered(
                    prose, self.thunk_factory(fn), condition=condition or AlwaysTrue()
                )
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
                Receive(h, self.thunk_factory(fn), condition=condition or AlwaysTrue())
            )
            return fn

        return wrap

    async def evaluate(
        self,
        command: str,
        world: Optional[World] = None,
        player: Optional[Entity] = None,
    ) -> Optional[Action]:
        assert player

        entity = await session.get().materialize(key=self.entity_key)
        assert entity

        log.debug("%s evaluate %s", self, entity)

        for registered in [r for r in self.registered if r.condition.applies()]:

            def transformer_factory(**kwargs):
                assert world and player
                return SimplifiedTransformer(
                    registered=registered,
                    world=world,
                    player=player,
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

        return None

    async def notify(self, ev: Event, **kwargs):
        entity = await session.get().materialize(key=self.entity_key)
        assert entity

        for receive in self.receives:
            if ev.name == receive.hook:
                try:
                    await receive.handler(this=entity, ev=ev, **kwargs)
                    tools.log_behavior(entity, dict(time=time.time(), success=True))
                except:
                    errors_log.exception("notify:exception", exc_info=True)
                    tools.log_behavior_exception(entity)


@dataclasses.dataclass(frozen=True)
class EntityAndBehavior:
    key: str
    behavior: str


class NoopEntityBehavior(EntityBehavior):
    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        return None

    async def notify(self, ev: Event, **kwargs):
        pass


@dataclasses.dataclass(frozen=True)
class CompiledEntityBehavior(EntityBehavior):
    simplified: Simplified
    assigned: Optional[grammars.CommandEvaluator]
    frame: Dict[str, Any] = dataclasses.field(repr=False)

    @property
    def hooks(self):
        return self.simplified.hooks

    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        log.debug("%s evaluate '%s'", self, command)
        action = await self.simplified.evaluate(command, **kwargs)
        if action:
            return action
        if self.assigned is not None:
            action = await self.assigned.evaluate(command, **kwargs)
            if action:
                return action
            return Unknown()
        return None

    async def notify(self, ev: Event, **kwargs):
        if isinstance(ev, DynamicPostMessage):
            log.info("notify: %s", ev)
            log.debug("notify: %s", self.frame)
            context = jsonpickle.unpickler.Unpickler()
            decoded = context.restore(
                ev.message, reset=True, classes=list(self.frame.values())
            )
            log.info("notify: %s", decoded)
            return await self.simplified.notify(decoded, **kwargs)
        else:
            log.debug("notify: %s", ev)
        return await self.simplified.notify(ev, **kwargs)


def _get_default_globals():
    # TODO Can we pass an exploded module here?
    event_classes = {k.__name__: k for k in get_all_events()}
    return dict(
        log=logging.getLogger("dimsum.dynamic.user"),
        dataclass=dataclasses.dataclass,
        Common=Common,
        tools=tools,
        Entity=Entity,
        Event=StandardEvent,
        PostMessage=inbox.PostMessage,
        Scope=Scope,
        Carryable=carryable.Carryable,
        fail=Failure,
        ok=Success,
        time=time.time,
        **event_classes,
    )


class DynamicParameterException(Exception):
    pass


def _prepare_args(fn, args, kwargs):
    def _get_arg(name):
        if name in kwargs:
            arg = kwargs[name]
            if isinstance(arg, inbox.PostService):
                return DynamicPostService(arg)
            if isinstance(arg, DynamicPostMessage):
                log.warning("DynamicPostMessage %s", arg)
            return arg
        if args:
            return args.pop(0)
        raise DynamicParameterException("'%s'" % (name,))

    signature = inspect.signature(fn)
    return [_get_arg(p) for p in signature.parameters]


@functools.lru_cache
def _compile(found: EntityAndBehavior) -> EntityBehavior:
    frame = _get_default_globals()

    def thunk_factory(fn):
        async def thunk(*args, **kwargs):
            log.info("thunking: args=%s kwargs=%s", args, kwargs)
            actual_args = _prepare_args(fn, list(args), kwargs)
            lokals: Dict[str, Any] = dict(thunk=(fn, actual_args, {}))
            frame.update(dict(ctx=context.get()))

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
                except Exception as e:
                    errors_log.exception("exception", exc_info=True)
                    errors_log.error("globals: %s", frame.keys())
                    errors_log.error("locals: %s", lokals)
                    errors_log.error("args: %s", args)
                    errors_log.error("kwargs: %s", kwargs)
                    raise e

            return await aexec()

        return thunk

    simplified = Simplified(found.key, thunk_factory)
    # TODO chain?
    frame.update(
        dict(
            language=simplified.language,
            received=simplified.received,
            hooks=simplified.hooks,
            Held=functools.partial(Held, found.key),
            Ground=functools.partial(Ground, found.key),
        )
    )

    log.info("compiling %s", found)

    tree = ast.parse(found.behavior)
    # TODO improve filename value here, we have entity.
    compiled = compile(tree, filename="<ast>", mode="exec")

    # We squash any declarations left in locals into our
    # globals so they're available in future calls via a
    # rebinding in our thunk factory above. I'm pretty sure
    # this is the only way to get this to behave.
    declarations: Dict[str, Any] = {}
    eval(compiled, frame, declarations)
    evaluator: Optional[grammars.CommandEvaluator] = None
    EvaluatorsName = "evaluators"
    if EvaluatorsName in declarations:
        evaluator = grammars.PrioritizedEvaluator(declarations[EvaluatorsName])
        del declarations[EvaluatorsName]
    frame.update(**declarations)
    return CompiledEntityBehavior(simplified, evaluator, declarations)


@dataclasses.dataclass
class Behavior:
    world: World
    entities: tools.EntitySet

    def _get_behaviors(self, e: Entity, c: Entity) -> List[EntityAndBehavior]:
        inherited = self._get_behaviors(e, c.parent) if c.parent else []
        with c.make_and_discard(behavior.Behaviors) as behave:
            b = behave.get_default()
            return (
                [EntityAndBehavior(e.key, b.python)]
                if b and b.executable and b.python
                else []
            ) + inherited

    @functools.cached_property
    def _behaviors(self) -> Dict[Entity, List[EntityAndBehavior]]:
        return {e: self._get_behaviors(e, e) for e in self.entities.all()}

    def _compile_behavior(
        self, entity: Entity, found: EntityAndBehavior
    ) -> EntityBehavior:
        try:
            return _compile(found)
        except Exception as e:
            errors_log.exception("dynamic:compile", exc_info=True)
            tools.log_behavior_exception(entity)
            return NoopEntityBehavior()

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

    async def notify(self, ev: Event, **kwargs):
        for target in [c for c in self._compiled]:
            await target.notify(ev, **kwargs)


def flatten(l):
    return [item for sl in l for item in sl]
