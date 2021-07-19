import logging
from typing import Type, Optional, Any

import grammars
import transformers
from model import *
from plugins.actions import PersonAction
import scopes.movement as movement
import scopes.occupyable as occupyable
import plugins.looking as looking

log = logging.getLogger("dimsum")


@hooks.all.enter.target
def can_enter(person: Entity, area: Entity) -> bool:
    return True


class Home(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        welcome_area = await materialize_well_known_entity(world, ctx, WelcomeAreaKey)
        return await Go(area=welcome_area).perform(
            world=world, area=area, person=person, ctx=ctx, **kwargs
        )


class MovingAction(PersonAction):
    def __init__(
        self,
        area: Optional[Entity] = None,
        finder: Optional[movement.FindsRoute] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.area = area
        self.finder = finder

    async def move(self, ctx: Ctx, world: World, person: Entity):
        area = await find_entity_area(person)

        destination = self.area

        if self.finder:
            log.info("finder: {0}".format(self.finder))
            area = await find_entity_area(person)
            route = await self.finder.find_route(
                area, person, world=world, builder=world
            )
            if route:
                routed = route.area
                destination = routed

        if destination is None:
            return Failure("where?")

        if not can_enter(person, destination):
            return Failure("sorry, you can't go there")

        with destination.make(occupyable.Occupyable) as entering:
            with area.make(occupyable.Occupyable) as leaving:
                await leaving.left(person)
                await entering.entered(person)

        return looking.AreaObservation(await find_entity_area(person), person)


class Go(MovingAction):
    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        return await self.move(ctx, world, person)


class Transformer(transformers.Base):
    def find_direction(self, args):
        return movement.FindDirectionalRoute(args[0])

    def find_route_by_gid(self, args):
        return movement.FindNavigableItem(args[0])

    def route(self, args):
        return args[0]

    def named_route(self, args):
        return movement.FindNamedRoute(str(args[0]))

    def home(self, args):
        return Home()

    def go(self, args):
        return Go(finder=args[0])


@grammars.grammar()
class MovingGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             go | home

        home:              "home"
        go:                "go" route

"""
