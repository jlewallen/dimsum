from typing import List, Tuple, Dict, Sequence, Optional
import abc
import logging
import enum

DefaultMoveVerb = "walk"
log = logging.getLogger("dimsum")


class Direction(enum.Enum):
    NORTH = 1
    SOUTH = 2
    WEST = 3
    EAST = 4

    @property
    def exiting(self) -> str:
        return str(self).split(".")[1]


class Area:
    @abc.abstractmethod
    def find_item_under(self, **kwargs):
        raise NotImplementedError("FindItemMixin required")

    @abc.abstractmethod
    def find_route(self, **kwargs):
        raise NotImplementedError


class AreaRoute:
    def __init__(self, area: Area = None):
        super().__init__()
        assert area
        self.area = area

    def satisfies(self, **kwargs) -> bool:
        return False

    def name(self) -> str:
        raise NotImplementedError


class VerbRoute(AreaRoute):
    def __init__(self, verb: str = None, **kwargs):
        super().__init__(**kwargs)
        assert verb
        self.verb = verb

    def satisfies(self, verb=None, **kwargs) -> bool:
        return verb and verb == self.verb

    def name(self) -> str:
        return self.verb


class DirectionalRoute(AreaRoute):
    def __init__(self, direction: Direction = None, **kwargs):
        super().__init__(**kwargs)
        assert direction
        self.direction = direction

    def satisfies(self, direction: Direction = None, **kwargs) -> bool:
        return self.direction == direction

    def name(self) -> str:
        return self.direction.exiting


class NavigationAction(enum.Enum):
    EXIT = 1
    ENTER = 2


class Navigable:
    def __init__(self, action: NavigationAction = None, **kwargs):
        super().__init__(**kwargs)  # type:ignore
        assert action
        self.action = action


class MovementMixin:
    def __init__(self, routes=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
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

    def adjacent(self) -> List[Area]:
        return [r.area for r in self.routes]

    def link_area(self, area: Area, verb=DefaultMoveVerb, **kwargs):
        return self.add_route(VerbRoute(area=area, verb=verb))

    def add_route(self, route: AreaRoute) -> AreaRoute:
        self.routes.append(route)
        log.debug("new route: {0} {1}".format(self, self.routes))
        return route


class FindsRoute:
    async def find_route(self, area: Area, person, **kwargs) -> Optional[AreaRoute]:
        raise NotImplementedError


class FindNamedRoute(FindsRoute):
    def __init__(self, name: str):
        super().__init__()
        assert name
        self.name = name

    async def find_route(self, area: Area, person, **kwargs) -> Optional[AreaRoute]:
        navigable = area.find_item_under(inherits=Navigable, q=self.name)
        if navigable:
            log.debug("navigable={0}".format(navigable))
            assert navigable.props.navigable
            return AreaRoute(area=navigable.props.navigable)
        return None


class FindDirectionalRoute(FindsRoute):
    def __init__(self, direction: Direction):
        super().__init__()
        self.direction = direction

    async def find_route(self, area: Area, person, **kwargs) -> Optional[AreaRoute]:
        navigable = area.find_item_under(inherits=Navigable, q=self.direction.exiting)
        if navigable:
            log.debug("navigable={0}".format(navigable))
            assert navigable.props.navigable
            return AreaRoute(area=navigable.props.navigable)
        return None


class FindNavigableItem(FindsRoute):
    def __init__(self, finder):
        super().__init__()
        assert finder
        self.finder = finder

    async def find_route(self, area: Area, person, **kwargs) -> Optional[AreaRoute]:
        area = self.finder.find_item(**kwargs)
        assert area
        return AreaRoute(area=area)
