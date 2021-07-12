import enum
import logging
from typing import List, Optional, Tuple

from model import Entity, Scope, Acls, context
import scopes.carryable as carryable

DefaultMoveVerb = "walk"
log = logging.getLogger("dimsum.scopes")


class Direction(enum.Enum):
    NORTH = 1
    SOUTH = 2
    WEST = 3
    EAST = 4

    @property
    def exiting(self) -> str:
        return str(self).split(".")[1]


class AreaRoute:
    def __init__(self, area: Optional[Entity] = None):
        super().__init__()
        assert area
        self.area = area

    def satisfies(self, **kwargs) -> bool:
        return False

    def name(self) -> str:
        raise NotImplementedError


class VerbRoute(AreaRoute):
    def __init__(self, verb: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        assert verb
        self.verb = verb

    def satisfies(self, verb=None, **kwargs) -> bool:
        return verb and verb == self.verb

    def name(self) -> str:
        return self.verb


class DirectionalRoute(AreaRoute):
    def __init__(self, direction: Optional[Direction] = None, **kwargs):
        super().__init__(**kwargs)
        assert direction
        self.direction = direction

    def satisfies(self, direction: Optional[Direction] = None, **kwargs) -> bool:
        return self.direction == direction

    def name(self) -> str:
        return self.direction.exiting


class Movement(Scope):
    def __init__(self, routes=None, **kwargs):
        super().__init__(**kwargs)
        self.routes: List[AreaRoute] = routes if routes else []

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

    def link_area(self, area: Entity, verb=DefaultMoveVerb, **kwargs):
        return self.add_route(VerbRoute(area=area, verb=verb))

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


class Exit(Scope):
    def __init__(self, area: Optional[Entity] = None, **kwargs):
        super().__init__(**kwargs)
        self.acls = Acls("exit")
        self.area = area if area else None


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
                new_area = navigable.make(Exit).area
                assert new_area
                return AreaRoute(area=new_area)
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
                new_area = navigable.make(Exit).area
                assert new_area
                return AreaRoute(area=new_area)
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
