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


class Area:
    @abc.abstractmethod
    def find_item_under(self, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def find_route(self, **kwargs):
        raise NotImplementedError


class AreaBuilder:
    @abc.abstractmethod
    def build_new_area(self, person, item, **kwargs) -> Area:
        pass


class AreaRoute:
    def __init__(self, area: Area = None, **kwargs):
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
        return str(self.direction).split(".")[1]


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
        log.debug("%s find-route: %s %s", self, self.routes, kwargs)
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
        log.debug("%s new route: %s", self, self.routes)
        return route

    def move_with(self, area, person, builder: AreaBuilder, **kwargs):
        if len(self.routes) == 0:
            destination = builder.build_new_area(person, self, **kwargs)
            self.link_area(destination, **kwargs)

        route = self.find_route(**kwargs)
        person.drop_here(area, item=self)
        return route


class FindsRoute:
    async def find_route(self, area, person, **kwargs) -> Optional[AreaRoute]:
        raise NotImplementedError


class FindNamedRoute(FindsRoute):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    async def find_route(
        self, area: Area, person, builder=None, **kwargs
    ) -> Optional[AreaRoute]:
        item = area.find_item_under(q=self.name, **kwargs)
        if not item:
            item = person.find_item_under(q=self.name, **kwargs)
            if not item:
                log.info("no named route: %s", self.name)
                return None

        log.info("named route: %s = %s", self.name, item)
        return item.move_with(area, person, builder=builder, **kwargs)


class FindDirectionalRoute(FindsRoute):
    def __init__(self, direction: Direction):
        super().__init__()
        self.direction = direction

    async def find_route(self, area: Area, person, **kwargs) -> Optional[AreaRoute]:
        return area.find_route(direction=self.direction)
