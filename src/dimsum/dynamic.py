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
import model.scopes.behavior as behavior

import context
import grammars
import transformers

log = logging.getLogger("dimsum.dynamic")


@dataclasses.dataclass(frozen=True)
class Registered:
    prose: str
    handler: Callable
    condition: "Condition"


@dataclasses.dataclass
class DynamicMessage(events.StandardEvent):
    message: game.Reply

    def render_string(self) -> Dict[str, str]:
        return json.loads(json.dumps(self.message))  # TODO json fuckery


@dataclasses.dataclass
class Say:
    everyone_queue: List[game.Reply] = dataclasses.field(default_factory=list)
    nearby_queue: List[game.Reply] = dataclasses.field(default_factory=list)
    player_queue: List[game.Reply] = dataclasses.field(default_factory=list)

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

    async def publish(self, area: entity.Entity, player: entity.Entity):
        for e in self.player_queue:
            await context.get().publish(
                DynamicMessage(
                    living=player,
                    area=area,
                    heard=[player],
                    message=e,
                )
            )
        heard = tools.default_heard_for(area)
        for e in self.nearby_queue:
            await context.get().publish(
                DynamicMessage(
                    living=player,
                    area=area,
                    heard=heard,
                    message=e,
                )
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

    async def perform(
        self, world: world.World, area: entity.Entity, person: entity.Entity, **kwargs
    ):
        try:
            say = Say()
            r = self.registered.handler(self.entity, *self.args, say=say)
            if r:
                log.info("say: %s", say)
                await say.publish(area, person)
                return self._transform_reply(r)
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


class Condition:
    def applies(self, player: entity.Entity, e: entity.Entity) -> bool:
        return True


class Held(Condition):
    def applies(self, player: entity.Entity, e: entity.Entity) -> bool:
        return tools.is_holding(player, e)


class Simplified:
    def __init__(self):
        self.registered: List[Registered] = []

    def language(self, prose: str, condition=None):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(
                Registered(prose, fn, condition=condition or Condition())
            )
            return fn

        return wrap

    def evaluate(
        self,
        command: str,
        world: Optional[world.World] = None,
        player: Optional[entity.Entity] = None,
        entity: Optional[entity.Entity] = None,
    ) -> Optional[game.Action]:
        assert world
        assert player
        assert entity

        for registered in [
            r for r in self.registered if r.condition.applies(player, entity)
        ]:

            def transformer_factory(**kwargs):
                assert world
                assert player
                assert entity
                return SimplifiedTransformer(
                    registered=registered, entity=entity, world=world, player=player
                )

            evaluator = grammars.GrammarEvaluator(registered.prose, transformer_factory)

            action = evaluator.evaluate(command)
            if action:
                return action

        return None


@dataclasses.dataclass(frozen=True)
class Found:
    entity: entity.Entity
    behavior: behavior.Behavior


@dataclasses.dataclass(frozen=True)
class Compiled(grammars.CommandEvaluator):
    entity: entity.Entity
    behavior: behavior.Behavior
    simplified: Simplified

    def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        return self.simplified.evaluate(command, entity=self.entity, **kwargs)


class Behavior:
    def __init__(self, world: world.World, player: entity.Entity):
        self.world = world
        self.player = player
        self.area = world.find_person_area(player)
        self.player_queue: List[game.Reply] = []
        self.everyone_queue: List[game.Reply] = []
        assert self.area

    @functools.cached_property
    def entities(self) -> tools.EntitySet:
        return tools.get_contributing_entities(self.world, self.area, self.player)

    def _get_behaviors(self, e: entity.Entity) -> List[Found]:
        with e.make_and_discard(behavior.Behaviors) as behave:
            b = behave.get_default()
            return [Found(e, b)] if b else []

    @functools.cached_property
    def behaviors(self) -> List[Found]:
        return flatten([self._get_behaviors(e) for e in self.entities.all()])

    def _say_everyone(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.everyone_queue.append(r)

    def _say_player(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.player_queue.append(r)

    def _get_globals(self, **kwargs):
        return dict(
            log=log,
            player=self.player,
            area=self.area,
            world=self.world,
            Held=Held,
            **kwargs,
        )

    def _compile_behaviors(self, found: Found) -> Compiled:
        simplified = Simplified()
        gs = self._get_globals(
            language=simplified.language,
        )
        for b in [b for b in self.behaviors if b.behavior.python]:
            try:
                tree = ast.parse(b.behavior.python)
                # TODO improve filename value here, we have entity.
                compiled = compile(tree, filename="<ast>", mode="exec")
                eval(compiled, gs, dict())
            except:
                log.exception("dynamic:error", exc_info=True)
        return Compiled(found.entity, found.behavior, simplified)

    @functools.cached_property
    def evaluators(self) -> List[grammars.CommandEvaluator]:
        return [self._compile_behaviors(f) for f in self.behaviors]


def flatten(l):
    return [item for sl in l for item in sl]
