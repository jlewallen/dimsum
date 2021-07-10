import logging
from typing import List, Optional, Type

import grammars
import transformers
from model import *
import scopes.carryable as carryable
import scopes.movement as movement
import scopes
from plugins.actions import PersonAction

log = logging.getLogger("dimsum")


class DigDirection:
    def __init__(
        self,
        arbitrary: Optional[str] = None,
        direction: Optional[movement.Direction] = None,
    ):
        super().__init__()
        self.arbitrary = arbitrary
        self.direction = direction

    @property
    def name(self):
        if self.direction:
            return self.direction.exiting
        if self.arbitrary:
            return self.arbitrary
        raise Exception("malformed dig")


class DigLinkage:
    def __init__(
        self,
        directions: Optional[List[DigDirection]] = None,
    ):
        super().__init__()
        assert directions
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


class Dig(PersonAction):
    def __init__(
        self,
        linkage: Optional[DigLinkage] = None,
        area_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__()
        assert linkage
        assert area_name
        self.linkage = linkage
        self.area_name = area_name

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        log.info(
            "digging {0} via {1} from {2}".format(self.area_name, self.linkage, area)
        )

        digging = scopes.area(
            creator=person,
            props=Common(name=self.area_name),
        )

        if self.linkage.there:
            goes_there = scopes.exit(
                creator=person,
                props=Common(name=self.linkage.there.name),
                initialize={movement.Exit: dict(area=digging)},
            )
            with area.make(carryable.Containing) as ground:
                ground.add_item(goes_there)
            ctx.register(goes_there)

        if self.linkage.back:
            comes_back = scopes.exit(
                creator=person,
                props=Common(name=self.linkage.back.name),
                initialize={movement.Exit: dict(area=area)},
            )
            with digging.make(carryable.Containing) as ground:
                ground.add_item(comes_back)
            ctx.register(comes_back)

        ctx.register(digging)

        return Success("dug and done")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

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


class Transformer(transformers.Base):
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
