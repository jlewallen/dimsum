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
    def find(self, q: str):
        pass

    @abc.abstractmethod
    def find_route(self, **kwargs):
        pass


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


class VerbRoute(AreaRoute):
    def __init__(self, verb: str = None, **kwargs):
        super().__init__(**kwargs)
        assert verb
        self.verb = verb

    def satisfies(self, verb=None, **kwargs) -> bool:
        return verb and verb == self.verb


class DirectionalRoute(AreaRoute):
    def __init__(self, direction: Direction = None, **kwargs):
        super().__init__(**kwargs)
        assert direction
        self.direction = direction

    def satisfies(self, direction: Direction = None, **kwargs) -> bool:
        return self.direction == direction


class MovementMixin:
    def __init__(self, routes=None, **kwargs):
        super().__init__(**kwargs)
        self.routes: List[AreaRoute] = routes if routes else []

    def find_route(self, **kwargs) -> Optional[AreaRoute]:
        log.info("find-route: %s %s", kwargs, self.routes)
        for r in self.routes:
            if r.satisfies(**kwargs):
                return r
        return None

    def link_area(self, area: Area, verb=DefaultMoveVerb, **kwargs):
        return self.add_route(VerbRoute(area=area, verb=verb))

    def add_route(self, route: AreaRoute) -> AreaRoute:
        self.routes.append(route)
        return route

    def move_with(self, area, person, builder: AreaBuilder, verb=None):
        if len(self.routes) == 0:
            destination = builder.build_new_area(person, self, verb=verb)
            self.link_area(destination, verb=verb)

        route = self.find_route(verb=verb)
        person.drop_here(area, item=self)
        return route


class FindsRoute:
    async def find(self, area, person, **kwargs) -> Optional[AreaRoute]:
        raise Exception("unimplemented")


class FindNamedRoute(FindsRoute):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    async def find(
        self, area: Area, person, builder=None, **kwargs
    ) -> Optional[AreaRoute]:
        item = area.find(self.name)
        if not item:
            item = person.find(self.name)
            if not item:
                log.info("no named route: %s", self.name)
                return None

        log.info("named route: %s = %s", self.name, item)
        return item.move_with(area, person, builder=builder, **kwargs)


class FindDirectionalRoute(FindsRoute):
    def __init__(self, direction: Direction):
        super().__init__()
        self.direction = direction

    async def find(self, area: Area, person, **kwargs) -> Optional[AreaRoute]:
        return area.find_route(direction=self.direction)
