import stringcase
import dataclasses
from typing import Tuple, Dict, List, Optional, Callable

from loggers import get_logger
from model import Entity, World, Common
from domains import Session
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.mechanics as mechanics
import scopes.movement as movement
import scopes.occupyable as occupyable
import scopes as scopes
import tools
from .trains import TrainFactory, Defaults

log = get_logger("dimsum.model")


def add_item(container: Entity, item: Entity):
    with container.make(carryable.Containing) as contain:
        contain.add_item(item)


class Generics:
    def __init__(self, world: World):
        self.thing = scopes.item(
            creator=world,
            props=Common("generic thing"),
        )
        self.area = scopes.area(
            creator=world,
            props=Common("generic area"),
        )
        self.player = scopes.alive(
            creator=world,
            props=Common("generic player"),
        )

    @property
    def all(self):
        return [self.thing, self.player, self.area]


class Factory:
    def create(self, world: World, generics: Generics):
        raise NotImplementedError


class Hammer(Factory):
    def create(self, world: World, generics: Generics):
        return scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common("Hammer", desc="It's heavy."),
        )


class BeerKeg(Factory):
    def create(self, world: World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common("Beer Keg", desc="It's heavy."),
        )
        return item


class LargeMapleTree(Factory):
    def create(self, world: World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common("Large Maple Tree", desc="It's heavy."),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@ds.received(TickEvent)
async def tick(this, ev, say, ctx):
  item = ctx.create_item(
    creator=this,
    kind=this.get_kind("leaf-1"),
    props=Common("Maple Leaf"),
    initialize={ Carryable: dict(quantity=1, kind=this.get_kind("leaf-1")) },
    register=False,
  )
  tools.hold(tools.area_of(this), item)
  say.nearby(this, "a Maple Leaf gently floats to the ground")
""",
            )
        return item


class LargeOakTree(Factory):
    def create(self, world: World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common("Large Oak Tree", desc="It's heavy."),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@ds.received(TickEvent)
async def tick(this, ev, say, ctx):
  item = ctx.create_item(
    creator=this,
    kind=this.get_kind("leaf-1"),
    props=Common("Oak Leaf"),
    initialize={ Carryable: dict(quantity=1, kind=this.get_kind("leaf-1")) },
    register=False,
  )
  tools.hold(tools.area_of(this), item)
  say.nearby(this, "an Oak Leaf gently floats to the ground")
""",
            )
        return item


class SmallCrevice:
    def create(self, world: World, generics: Generics, area: Entity):
        item = scopes.exit(
            creator=world,
            parent=generics.thing,
            visible=mechanics.Visible(hard_to_see=True),
            initialize={movement.Exit: dict(area=area)},
            props=Common(
                "Small Crevice",
                desc="Whoa, how'd you even find this!?",
            ),
        )
        return item


class MysteriousBox(Factory):
    def create(self, world: World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common(
                "Mysterious Box",
                desc="It looks like some weird antique your grandmother would have. Why would anyone carry this thing around?",
            ),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="#",
            )
        return item


class LargeSteepCliff(Factory):
    def create(self, world: World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common(
                "Large Steep Cliff",
                desc="It's immense, with rocky outcroppings. It looks very climbable.",
            ),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@ds.received(TickEvent)
async def tick(this, ev, say, ctx):
  item = ctx.create_item(
    creator=this,
    kind=this.get_kind("pebble-1"),
    props=Common("Pebble"),
    initialize={ Carryable: dict(quantity=3, kind=this.get_kind("pebble-1")) },
    register=False,
  )
  tools.hold(tools.area_of(this), item)
  say.nearby(this, "some Pebbles tumbled down the cliff")
""",
            )
        return item


class Guitar(Factory):
    def create(self, world: World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=Common("Acoustic Guitar", desc="Seems to be well travelled."),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="",
            )
        return item


class WoodenLadder:
    def create(self, world: World, generics: Generics, area: Entity):
        item = scopes.exit(
            creator=world,
            parent=generics.thing,
            props=Common("Wooden Ladder", desc="Seems sturdy enough."),
            initialize={movement.Exit: dict(area=area)},
        )
        return item


class TomorrowCat(Factory):
    def create(self, world: World, generics: Generics):
        animal = scopes.alive(
            creator=world,
            parent=generics.thing,
            props=Common(
                "Tomorrow", desc="She's a Maine Coon, and very elegant and pretty."
            ),
        )
        return animal


class CavernEntrance:
    def create(self, world: World, generics: Generics, area: Entity):
        area = scopes.exit(
            creator=world,
            parent=generics.area,
            props=Common(
                "Entrance to a Dark Cavern",
                desc="It's dark, the cavern that is.",
            ),
            initialize={movement.Exit: dict(area=area)},
        )
        return area


class DarkCavern(Factory):
    def create(self, world: World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=Common(
                "Dark Cavern",
                desc="It's dark",
            ),
        )

        return area


class ArtistsLoft(Factory):
    def create(self, world: World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=Common(
                "Artist's Loft",
                desc="Everything is very colorful, because everything has got paint on it.",
            ),
        )
        return area


def add_directional(
    world: World,
    fr: Entity,
    to: Entity,
    direction: movement.Direction,
    generics: Generics,
):
    add_item(
        fr,
        scopes.exit(
            creator=world,
            parent=generics.thing,
            props=Common(name=direction.exit_name),
            initialize={movement.Exit: dict(area=to)},
        ),
    )


class RoomGrid(Factory):
    def __init__(self, w=1, h=1, **kwargs):
        super().__init__()
        self.w = w
        self.h = h

    def make_cell(self, world: World, generics: Generics, x, y):
        name = "Grid Room %d x %x" % (x, y)
        return scopes.area(
            creator=world,
            parent=generics.area,
            props=Common(name, desc=name),
        )

    def create(self, world: World, generics: Generics):
        grid = [
            [self.make_cell(world, generics, y, x) for x in range(self.w)]
            for y in range(self.h)
        ]

        def add_doorway(from_cell, to_cell, direction):
            add_directional(world, from_cell, to_cell, direction, generics)

        def link_cells(cell1, cell2, direction):
            add_doorway(cell2, cell1, direction)

        def try_add(cell, ox, oy, x, y, direction):
            if y < 0 or y >= len(grid):
                return
            row = grid[y]
            if x < 0 or x >= len(row):
                return
            from_cell = grid[ox][oy]
            to_cell = grid[x][y]
            add_doorway(from_cell, to_cell, direction)

        for x in range(self.w):
            for y in range(self.h):
                try_add(grid[x][y], x, y, x, y + 1, movement.Direction.NORTH)
                try_add(grid[x][y], x, y, x, y - 1, movement.Direction.SOUTH)
                try_add(grid[x][y], x, y, x + 1, y, movement.Direction.EAST)
                try_add(grid[x][y], x, y, x - 1, y, movement.Direction.WEST)

        return grid[0][0]


class Museum(Factory):
    def create(self, world: World, generics: Generics):
        return RoomGrid(w=3, h=3).create(world, generics)


class MarbleSteps:
    def create(self, world: World, generics: Generics, area: Entity):
        item = scopes.exit(
            creator=world,
            parent=generics.thing,
            props=Common("Marble Steps", desc="Marble"),
            initialize={movement.Exit: dict(area=area)},
        )
        return item


class NarrowCanyon:
    def create(self, world: World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=Common(
                "Narrow Canyon",
                desc="It's barely wide enough to walk two by two down. The narrow walls really funnel the wind, creating powerful gusts.",
            ),
        )
        with area.make(mechanics.Weather) as weather:
            weather.wind = mechanics.Wind(magnitude=50)
        return area


class RockyPath:
    def create(self, world: World, generics: Generics, area: Entity):
        item = scopes.exit(
            creator=world,
            parent=generics.thing,
            props=Common("Rocky Path", desc="Looks easy enough"),
            initialize={movement.Exit: dict(area=area)},
        )
        return item


class WelcomeArea(Factory):
    def create(self, world: World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=Common(
                "Town Courtyard",
                desc="""A quaint, small town courtyard. Trees overhang the cobblestone sidewalks that segment the green. A damp, smokey smell wafts through the air. Along the edges of a large, well maintained parkland, there are several small, older buildings. Some of them appear to be very new and a few look embarrassingly modern.

You can tell it's an easy place to ask for `help` and that people are eager for you to `look`  around and, when you're comfortable, even `go` places.

Welcome! :)
""",
            ),
        )
        add_item(area, BeerKeg().create(world, generics))
        add_item(area, LargeOakTree().create(world, generics))
        add_item(area, Hammer().create(world, generics))
        add_item(area, MysteriousBox().create(world, generics))
        add_item(area, Guitar().create(world, generics))
        add_item(area, LargeSteepCliff().create(world, generics))
        with area.make(occupyable.Occupyable) as entering:
            entering.add_living(TomorrowCat().create(world, generics))

        loft = ArtistsLoft().create(world, generics)
        add_item(area, WoodenLadder().create(world, generics, loft))
        add_item(loft, WoodenLadder().create(world, generics, area))

        canyon = NarrowCanyon().create(world, generics)
        add_item(area, RockyPath().create(world, generics, canyon))
        add_item(canyon, RockyPath().create(world, generics, area))

        clearing = scopes.area(
            creator=world,
            parent=generics.area,
            props=Common("A small clearing."),
        )
        add_item(
            area,
            scopes.exit(
                creator=world,
                parent=generics.thing,
                props=Common("Worn Path"),
                initialize={movement.Exit: dict(area=clearing)},
            ),
        )
        add_item(
            clearing,
            scopes.exit(
                creator=world,
                parent=generics.thing,
                props=Common("Worn Path"),
                initialize={movement.Exit: dict(area=area)},
            ),
        )

        add_item(clearing, LargeMapleTree().create(world, generics))

        cavern = DarkCavern().create(world, generics)
        add_item(clearing, CavernEntrance().create(world, generics, cavern))
        add_item(cavern, SmallCrevice().create(world, generics, clearing))

        museum = Museum().create(world, generics)
        add_item(clearing, MarbleSteps().create(world, generics, museum))
        add_item(museum, MarbleSteps().create(world, generics, clearing))

        return area


@dataclasses.dataclass
class KtownAreas:
    wilshire_western: Entity
    wilshire_normandie: Entity
    outside_bounty: Entity


def create_ktown(world: World, generics: Generics) -> KtownAreas:
    wilshire_western = scopes.area(creator=world, props=Common("Wilshire/Western"))
    wilshire_normandie = scopes.area(creator=world, props=Common("Wilshire/Normandie"))
    outside_bounty = scopes.area(creator=world, props=Common("Outside the Bounty"))
    add_directional(
        world, outside_bounty, wilshire_normandie, movement.Direction.NORTH, generics
    )
    add_directional(
        world, wilshire_normandie, outside_bounty, movement.Direction.SOUTH, generics
    )
    return KtownAreas(wilshire_western, wilshire_normandie, outside_bounty)


def bidirectional(world: World, a: Entity, b: Entity, name: str, generics: Generics):
    add_item(
        a,
        scopes.exit(
            creator=world,
            parent=generics.thing,
            props=Common(name),
            initialize={movement.Exit: dict(area=b)},
        ),
    )
    add_item(
        b,
        scopes.exit(
            creator=world,
            parent=generics.thing,
            props=Common(name),
            initialize={movement.Exit: dict(area=a)},
        ),
    )


def _create_example_world(world: World) -> Tuple[Generics, Entity]:
    generics = Generics(world)
    area = WelcomeArea().create(world, generics)
    return generics, area


def example_world_factory(world: World) -> Callable:
    async def factory(session: Session):
        generics, area = _create_example_world(world)

        ktown = create_ktown(world, generics)

        bidirectional(
            world, area, ktown.wilshire_normandie, "Torn-up Sidewak", generics
        )

        stops: List[str] = [ktown.wilshire_normandie.key, ktown.wilshire_western.key]

        factory = TrainFactory(
            defaults=Defaults(
                interior_name="Purple Line Car",
                enter_name="Purple Line Train",
                leave_name="Train Door",
                stops=stops,
            )
        )

        session.register(generics.all)

        await session.add_area(area)
        await session.add_area(ktown.wilshire_western)

        with session.ctx() as ctx:
            train = await factory.create(world, ctx)

    return factory
