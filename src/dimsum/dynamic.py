from typing import Callable, List, Dict, Optional, Any, Union, Sequence

import logging
import dataclasses
import ast
import functools
import json

import lark

import model.game as game
import model.reply as reply
import model.world as world
import model.entity as entity
import model.tools as tools
import model.events as events
import model.things as things
import model.scopes.behavior as behavior

import context
import grammars
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


@dataclasses.dataclass
class Receive:
    hook: str
    handler: Callable
    condition: Condition


@dataclasses.dataclass
class DynamicMessage(events.StandardEvent):
    message: game.Reply

    def render_string(self) -> Dict[str, str]:
        return json.loads(json.dumps(self.message))  # TODO json fuckery


@dataclasses.dataclass
class Notify:
    entity: entity.Entity
    hook: str
    kwargs: Dict[str, Any]


@dataclasses.dataclass
class Say:
    notified: List[Notify] = dataclasses.field(default_factory=list)
    everyone_queue: List[game.Reply] = dataclasses.field(default_factory=list)
    nearby_queue: List[game.Reply] = dataclasses.field(default_factory=list)
    player_queue: List[game.Reply] = dataclasses.field(default_factory=list)

    def notify(self, entity: entity.Entity, message: str, **kwargs):
        self.notified.append(Notify(entity, message, kwargs))

    def everyone(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.everyone_queue.append(r)

    def nearby(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.player_queue.append(r)

    def player(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.player_queue.append(r)

    async def _pub(self, **kwargs):
        await context.get().publish(DynamicMessage(**kwargs))

    async def publish(self, area: entity.Entity, player: entity.Entity):
        for e in self.player_queue:
            await self._pub(
                living=player,
                area=area,
                heard=[player],
                message=e,
            )

        heard = tools.default_heard_for(area)
        for e in self.nearby_queue:
            await self._pub(
                living=player,
                area=area,
                heard=heard,
                message=e,
            )


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
        dynamic_behavior: Optional["Behavior"] = None,
        **kwargs
    ):
        assert dynamic_behavior
        try:
            say = Say()
            args = await self._args(world, person)
            reply = self.registered.handler(self.entity, *args, say=say)
            if reply:
                log.debug("say: %s", say)
                for notify in say.notified:
                    await dynamic_behavior.notify(notify, say=say)
                await say.publish(area, person)
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


@dataclasses.dataclass
class Simplified:
    registered: List[Registered] = dataclasses.field(default_factory=list)
    receives: List[Receive] = dataclasses.field(default_factory=list)

    def language(self, prose: str, condition=None):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(
                Registered(prose, fn, condition=condition or Condition())
            )
            return fn

        return wrap

    def received(self, hook: str, condition=None):
        def wrap(fn):
            log.info("hook: '%s' %s", hook, fn)
            self.receives.append(Receive(hook, fn, condition=condition or Condition()))
            return fn

        return wrap

    async def notify(self, entity: entity.Entity, notify: Notify, **kwargs):
        for receive in self.receives:
            log.info("notifying %s notify=%s kwargs=%s", receive, notify, kwargs)
            receive.handler(entity, notify.entity, **kwargs)

    def evaluate(
        self,
        command: str,
        world: Optional[world.World] = None,
        player: Optional[entity.Entity] = None,
        entity: Optional[entity.Entity] = None,
    ) -> Optional[game.Action]:
        assert player
        assert entity
        for registered in [
            r for r in self.registered if r.condition.applies(player, entity)
        ]:

            def transformer_factory(**kwargs):
                assert world and player and entity
                return SimplifiedTransformer(
                    registered=registered, entity=entity, world=world, player=player
                )

            evaluator = grammars.GrammarEvaluator(registered.prose, transformer_factory)

            action = evaluator.evaluate(command)
            if action:
                return action

        return None


@dataclasses.dataclass(frozen=True)
class EntityAndBehavior:
    entity: entity.Entity
    behavior: behavior.Behavior


@dataclasses.dataclass(frozen=True)
class Compiled(grammars.CommandEvaluator):
    entity: entity.Entity
    behavior: behavior.Behavior
    simplified: Simplified

    def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        return self.simplified.evaluate(command, entity=self.entity, **kwargs)

    async def notify(self, notify: Notify, **kwargs):
        await self.simplified.notify(self.entity, notify, **kwargs)


class Behavior:
    def __init__(self, world: world.World, player: entity.Entity):
        self.world = world
        self.player = player
        self.area = world.find_person_area(player)
        assert self.area

    @functools.cached_property
    def entities(self) -> tools.EntitySet:
        return tools.get_contributing_entities(self.world, self.area, self.player)

    def _get_behaviors(self, e: entity.Entity) -> List[EntityAndBehavior]:
        with e.make_and_discard(behavior.Behaviors) as behave:
            b = behave.get_default()
            return [EntityAndBehavior(e, b)] if b else []

    @functools.cached_property
    def _behaviors(self) -> List[EntityAndBehavior]:
        return flatten([self._get_behaviors(e) for e in self.entities.all()])

    def _get_globals(self, **kwargs):
        return dict(
            log=log,
            player=self.player,
            area=self.area,
            world=self.world,
            Held=Held,
            Ground=Ground,
            fail=game.Failure,
            ok=game.Success,
            **kwargs,
        )

    def _compile_behavior(self, found: EntityAndBehavior) -> Compiled:
        simplified = Simplified()
        gs = self._get_globals(
            language=simplified.language,
            received=simplified.received,
        )
        log.info("compiling %s", found)
        try:
            tree = ast.parse(found.behavior.python)
            # TODO improve filename value here, we have entity.
            compiled = compile(tree, filename="<ast>", mode="exec")
            eval(compiled, gs, dict())
        except:
            log.exception("dynamic:error", exc_info=True)
        return Compiled(found.entity, found.behavior, simplified)

    @functools.cached_property
    def compiled(self) -> Sequence[Compiled]:
        return [self._compile_behavior(f) for f in self._behaviors if f.behavior.python]

    @property
    def evaluators(self) -> List[grammars.CommandEvaluator]:
        return list(self.compiled)

    async def notify(self, notify: Notify, **kwargs):
        for target in self.compiled:
            if target.entity.key == notify.entity.key:
                await target.notify(notify, **kwargs)


def flatten(l):
    return [item for sl in l for item in sl]
