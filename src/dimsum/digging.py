from typing import Any, List, Type

import logging

import grammar
import evaluator

import properties
import movement
import actions
import carryable

from context import *
from reply import *
from game import *
from things import *
from envo import *
from living import *
from animals import *
from events import *
from world import *

log = logging.getLogger("dimsum")


class DigDirection:
    def __init__(self, arbitrary: str = None, direction: movement.Direction = None):
        super().__init__()
        self.arbitrary = arbitrary
        self.direction = direction

    @property
    def name(self):
        if self.direction:
            return self.direction.exiting
        if self.arbitrary:
            return self.arbitrary
        raise Error("malformed dig")


class DigLinkage:
    def __init__(
        self,
        directions: List[DigDirection] = None,
    ):
        super().__init__()
        self.directions = directions

    @property
    def there(self):
        if len(self.directions) >= 1:
            return self.directions[0]
        return None

    @property
    def back(self):
        if len(self.directions) >= 2:
            return self.directions[1]
        return None

    def __repr__(self):
        return "DigLinkage<{0}>".format(self.directions)


class Dig(actions.PersonAction):
    def __init__(self, linkage: DigLinkage = None, area_name: str = None, **kwargs):
        super().__init__(**kwargs)
        assert linkage
        assert area_name
        self.linkage = linkage
        self.area_name = area_name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)

        log.info(
            "digging {0} via {1} from {2}".format(self.area_name, self.linkage, area)
        )

        digging = envo.Area(
            creator=player,
            props=properties.Common(name=self.area_name),
        )

        if self.linkage.there:
            goes_there = envo.Exit(
                area=digging,
                creator=player,
                props=properties.Common(name=self.linkage.there.name),
            )
            with area.make(carryable.ContainingMixin) as ground:
                ground.add_item(goes_there)
            world.register(goes_there)

        if self.linkage.back:
            comes_back = envo.Exit(
                area=area,
                creator=player,
                props=properties.Common(name=self.linkage.back.name),
            )
            with digging.make(carryable.ContainingMixin) as ground:
                ground.add_item(comes_back)
            world.register(comes_back)

        world.register(digging)

        return Success("dug and done", created=[area])


@grammar.grammar()
class Grammar(grammar.Grammar):
    @property
    def evaluator(self) -> Type[evaluator.Evaluator]:
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:             dig

        dig_direction:     direction
        dig_arbitrary:     WORD
        dig_linkage:       dig_direction | dig_arbitrary
        dig_linkages:      dig_linkage ("|" dig_linkage)*
        dig:               "dig" dig_linkages "to" string -> dig
"""


class Evaluator(evaluator.Evaluator):
    def dig(self, args):
        return Dig(args[0], args[1])

    def dig_direction(self, args):
        return DigDirection(direction=args[0])

    def dig_arbitrary(self, args):
        return DigDirection(arbitrary=args[0])

    def dig_linkages(self, args):
        return DigLinkage(args)

    def dig_linkage(self, args):
        return args[0]
