import ast
import dataclasses
import functools
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import context
import grammars
import model.entity as entity
import model.events as events
import model.game as game
import model.properties as properties
import model.scopes.behavior as behavior
import model.scopes.carryable as carryable
import model.things as things
import model.tools as tools
import model.world as world
import saying
import transformers

log = logging.getLogger("dimsum.dynamic")


class Condition:
    def applies(self, person: entity.Entity, e: entity.Entity) -> bool:
        return True


class Held(Condition):
    def applies(self, person: entity.Entity, e: entity.Entity) -> bool:
        return tools.is_holding(person, e)


class Ground(Condition):
    def applies(self, person: entity.Entity, e: entity.Entity) -> bool:
        return not tools.is_holding(person, e)


@dataclasses.dataclass(frozen=True)
class Registered:
    prose: str
    handler: Callable
    condition: Condition


@dataclasses.dataclass(frozen=True)
class Receive:
    hook: str
    handler: Callable
    condition: Condition


class EntityBehavior(grammars.CommandEvaluator):
    async def notify(self, notify: saying.Notify, **kwargs):
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class SimplifiedAction(game.Action):
    entity: entity.Entity
    registered: Registered
    args: List[Any]

    def _transform_reply(self, r: Union[game.Reply, str]) -> game.Reply:
        if isinstance(r, str):
            return game.Success(r)
        return r

    async def _transform_arg(
        self, arg: things.ItemFinder, world: world.World, person: entity.Entity
    ) -> Optional[entity.Entity]:
        assert isinstance(arg, things.ItemFinder)
        return await world.apply_item_finder(person, arg)

    async def _args(self, world: world.World, person: entity.Entity) -> List[Any]:
        return [await self._transform_arg(a, world, person) for a in self.args]

    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        **kwargs,
    ):
        try:
            say = saying.Say()
            args = await self._args(world, person)
            reply = await self.registered.handler(
                self.entity, *args, person=person, say=say
            )
            if reply:
                log.debug("say: %s", say)
                await say.publish(area)
                return self._transform_reply(reply)
            return game.Failure("no reply from handler?")
        except Exception as e:
            log.exception("handler:error", exc_info=True)
            return game.DynamicFailure(str(e), str(self.registered.handler))


@dataclasses.dataclass
class SimplifiedTransformer(transformers.Base):
    registered: Registered
    entity: entity.Entity

    def start(self, args):
        return SimplifiedAction(self.entity, self.registered, args)


@dataclasses.dataclass(frozen=True)
class Simplified:
    entity: entity.Entity
    thunk_factory: Callable
    registered: List[Registered] = dataclasses.field(default_factory=list)
    receives: List[Receive] = dataclasses.field(default_factory=list)

    def language(self, prose: str, condition=None):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(
                Registered(
                    prose, self.thunk_factory(fn), condition=condition or Condition()
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
                Receive(h, self.thunk_factory(fn), condition=condition or Condition())
            )
            return fn

        return wrap

    async def evaluate(
        self,
        command: str,
        world: Optional[world.World] = None,
        player: Optional[entity.Entity] = None,
    ) -> Optional[game.Action]:
        assert player
        for registered in [
            r for r in self.registered if r.condition.applies(player, self.entity)
        ]:

            def transformer_factory(**kwargs):
                assert world and player
                return SimplifiedTransformer(
                    registered=registered,
                    world=world,
                    player=player,
                    entity=self.entity,
                )

            evaluator = grammars.GrammarEvaluator(registered.prose, transformer_factory)

            action = await evaluator.evaluate(command)
            if action:
                return action

        return None

    async def notify(self, notify: saying.Notify, **kwargs):
        for receive in self.receives:
            if notify.applies(receive.hook):
                await notify.invoke(receive.handler, self.entity, **kwargs)


@dataclasses.dataclass(frozen=True)
class EntityAndBehavior:
    entity: entity.Entity
    behavior: behavior.Behavior


class NoopEntityBehavior(EntityBehavior):
    async def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        return None

    async def notify(self, notify: saying.Notify, **kwargs):
        pass


@dataclasses.dataclass(frozen=True)
class CompiledEntityBehavior(EntityBehavior):
    simplified: Simplified
    assigned: Optional[grammars.CommandEvaluator] = None

    async def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        action = await self.simplified.evaluate(command, **kwargs)
        if action:
            return action
        if self.assigned is not None:
            action = await self.assigned.evaluate(command, **kwargs)
            if action:
                return action
            return game.Unknown()
        return None

    async def notify(self, notify: saying.Notify, **kwargs):
        return await self.simplified.notify(notify, **kwargs)


class Behavior:
    def __init__(self, world: world.World, entities: tools.EntitySet):
        self.world = world
        self.entities = entities
        self.globals: Dict[str, Any] = self._get_default_globals()
        self.locals: Dict[str, Any] = {}

    def _get_default_globals(self):
        # TODO Can we pass an exploded module here?
        event_classes = {k.__name__: k for k in events.get_all()}
        return dict(
            log=log,
            Held=Held,
            Ground=Ground,
            Scope=entity.Scope,
            properties=properties,
            Entity=entity.Entity,
            Carryable=carryable.Carryable,
            dataclass=dataclasses.dataclass,
            Event=events.StandardEvent,
            fail=game.Failure,
            tools=tools,
            ok=game.Success,
            **event_classes,
        )

    def _get_behaviors(self, e: entity.Entity) -> List[EntityAndBehavior]:
        with e.make_and_discard(behavior.Behaviors) as behave:
            b = behave.get_default()
            return [EntityAndBehavior(e, b)] if b else []

    @functools.cached_property
    def _behaviors(self) -> List[EntityAndBehavior]:
        return flatten([self._get_behaviors(e) for e in self.entities.all()])

    def _compile_behavior(self, found: EntityAndBehavior) -> EntityBehavior:
        def thunk_factory(fn):
            async def thunk(*args, **kwargs):
                async def aexec():
                    lokals = dict(thunk=(fn, args, kwargs))
                    exec(
                        """
# This seems to be an easy clever trick for capturing the global
# during the eval into the method?
async def __ex(t=thunk):
    return await t[0](*t[1], **t[2])""",
                        self.globals,
                        lokals,
                    )
                    try:
                        return await lokals["__ex"]()  # type:ignore
                    except:
                        log.exception("exception", exc_info=True)
                        log.error("globals: %s", self.globals.keys())
                        log.error("locals: %s", lokals)
                        log.error("args: %s", args)
                        log.error("kwargs: %s", kwargs)

                log.debug("thunking: %s args=%s kwargs=%s", fn, args, kwargs)
                log.debug("thunking: %s", inspect.signature(fn))
                self.globals.update(dict(ctx=context.get()))
                return await aexec()

            return thunk

        simplified = Simplified(found.entity, thunk_factory)
        self.globals.update(
            dict(
                language=simplified.language,
                received=simplified.received,
            )
        )

        log.info("compiling %s", found)
        try:
            tree = ast.parse(found.behavior.python)
            # TODO improve filename value here, we have entity.
            compiled = compile(tree, filename="<ast>", mode="exec")

            # We squash any declarations left in locals into our
            # globals so they're available in future calls via a
            # rebinding in our thunk factory above. I'm pretty sure
            # this is the only way to get this to behave.
            declarations: Dict[str, Any] = {}
            eval(compiled, self.globals, declarations)
            evaluator: Optional[grammars.CommandEvaluator] = None
            EvaluatorsName = "evaluators"
            if EvaluatorsName in declarations:
                evaluator = grammars.PrioritizedEvaluator(declarations[EvaluatorsName])
                del declarations[EvaluatorsName]
            self.globals.update(**declarations)
            return CompiledEntityBehavior(simplified, evaluator)
        except:
            log.exception("dynamic:error", exc_info=True)
            return NoopEntityBehavior()

    @functools.cached_property
    def _compiled(self) -> Sequence[EntityBehavior]:
        return [self._compile_behavior(f) for f in self._behaviors if f.behavior.python]

    @property
    def evaluator(self) -> grammars.CommandEvaluator:
        return grammars.PrioritizedEvaluator(self._compiled)

    async def notify(self, notify: saying.Notify, say=None):
        log.info("notify=%s n=%d", notify, len(self._compiled))
        say = saying.Say()
        for target in [c for c in self._compiled]:
            await target.notify(notify, say=say)
        # await say.publish(area, person) # TODO


def flatten(l):
    return [item for sl in l for item in sl]
