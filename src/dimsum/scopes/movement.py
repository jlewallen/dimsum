import enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from loggers import get_logger
from model import Entity, Scope, Acls, context
import scopes.carryable as carryable

log = get_logger("dimsum.scopes")


class Direction(enum.Enum):
    NORTH_EAST = "NORTHEAST"
    NORTH = "NORTH"
    NORTH_WEST = "NORTHWEST"
    WEST = "WEST"
    SOUTH = "SOUTH"
    SOUTH_WEST = "SOUTHWEST"
    EAST = "EAST"
    SOUTH_EAST = "SOUTHEAST"

    @property
    def exit_name(self) -> str:
        return "%s Exit" % (self.exiting.title(),)

    @property
    def exiting(self) -> str:
        return str(self).split(".")[1]


@dataclass
class Unavailable:
    """Definitely going with the simplest thing that'll work right
    now. I'm really curious about how this can be expanded. A key
    thing to remember is this is just an object creatred when making
    something unavailable. Reason should always be here."""

    reason: str


class AreaRoute:
    def __init__(
        self, area: Optional[Entity] = None, unavailable: Optional[Unavailable] = None
    ):
        super().__init__()
        assert area
        self.area = area
        self.unavailable = unavailable

    def satisfies(self, **kwargs) -> bool:
        return False

    def name(self) -> str:
        raise NotImplementedError


class DirectionalRoute(AreaRoute):
    def __init__(self, direction: Optional[Direction] = None, **kwargs):
        super().__init__(**kwargs)
        assert direction
        self.direction = direction

    def satisfies(self, direction: Optional[Direction] = None, **kwargs) -> bool:
        return self.direction == direction

    def name(self) -> str:
        return self.direction.exiting


@dataclass
class Movement(Scope):
    routes: List[AreaRoute] = field(default_factory=list)

    @property
    def available_routes(self) -> List[AreaRoute]:
        return self.routes

    @property
    def require_single_linked_area(self):
        return self.adjacent()[0]

    def find_route(self, **kwargs) -> Optional[AreaRoute]:
        log.debug("find-route: {0} {1} {2}".format(self, self.routes, kwargs))
        for r in self.routes:
            if r.satisfies(**kwargs):
                return r
        return None

    def add_route(self, route: AreaRoute) -> AreaRoute:
        self.routes.append(route)
        log.debug("new route: {0} {1}".format(self, self.routes))
        return route

    def adjacent(self) -> List[Entity]:
        areas: List[Entity] = []
        for e in self.ourselves.make(carryable.Containing).holding:
            maybe_area = e.make(Exit).area
            if maybe_area:
                areas.append(maybe_area)
        return areas + [r.area for r in self.routes]


@dataclass
class Exit(Scope):
    area: Optional[Entity] = None
    unavailable: Optional[Unavailable] = None
    acls: Acls = field(default_factory=Acls.owner_writes)


class FindsRoute:
    async def find_route(self, area: Entity, person, **kwargs) -> Optional[AreaRoute]:
        raise NotImplementedError


class FindNamedRoute(FindsRoute):
    def __init__(self, name: str):
        super().__init__()
        assert name
        self.name = name

    async def find_route(self, area: Entity, person, **kwargs) -> Optional[AreaRoute]:
        with area.make(carryable.Containing) as contain:
            navigable = await context.get().find_item(
                candidates=contain.holding, scopes=[Exit], q=self.name
            )
            if navigable:
                log.debug("navigable={0}".format(navigable))
                with navigable.make_and_discard(Exit) as exiting:
                    new_area = exiting.area
                    assert new_area
                    return AreaRoute(area=new_area, unavailable=exiting.unavailable)
        return None


class FindDirectionalRoute(FindsRoute):
    def __init__(self, direction: Direction):
        super().__init__()
        self.direction = direction

    async def find_route(self, area: Entity, person, **kwargs) -> Optional[AreaRoute]:
        with area.make(carryable.Containing) as contain:
            navigable = await context.get().find_item(
                candidates=contain.holding, scopes=[Exit], q=self.direction.exiting
            )
            if navigable:
                log.debug("navigable={0}".format(navigable))
                with navigable.make_and_discard(Exit) as exiting:
                    new_area = navigable.make(Exit).area
                    new_area = exiting.area
                    assert new_area
                    return AreaRoute(area=new_area, unavailable=exiting.unavailable)
        return None


class FindNavigableItem(FindsRoute):
    def __init__(self, finder):
        super().__init__()
        assert finder
        self.finder = finder

    async def find_route(self, area: Entity, person, **kwargs) -> Optional[AreaRoute]:
        area = await self.finder.find_item(**kwargs)
        assert area
        return AreaRoute(area=area)
