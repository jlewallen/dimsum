from typing import List, Tuple
import logging

import model.game as game
import model.properties as properties
import model.world as world
import model.entity as entity

import model.scopes.movement as movement
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable
import model.scopes.carryable as carryable
import model.scopes.behavior as behavior
import model.scopes as scopes

import actions

log = logging.getLogger("dimsum")


def add_item(container: entity.Entity, item: entity.Entity):
    with container.make(carryable.Containing) as contain:
        contain.add_item(item)


class Generics:
    def __init__(self, world: world.World):
        self.thing = scopes.item(
            creator=world,
            props=properties.Common("generic thing"),
        )
        self.area = scopes.area(
            creator=world,
            props=properties.Common("generic area"),
        )
        self.player = scopes.alive(
            creator=world,
            props=properties.Common("generic player"),
        )

    @property
    def all(self):
        return [self.thing, self.player, self.area]


class Factory:
    def create(self, world: world.World, generics: Generics):
        raise NotImplementedError


class Hammer(Factory):
    def create(self, world: world.World, generics: Generics):
        return scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common("Hammer", desc="It's heavy."),
        )


class BeerKeg(Factory):
    def create(self, world: world.World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common("Beer Keg", desc="It's heavy."),
        )
        return item


class LargeMapleTree(Factory):
    def create(self, world: world.World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common("Large Maple Tree", desc="It's heavy."),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                "b:drop-leaf:tick",
                lua="""
function(s, world, area, item)
    return area.make_here({
        kind = item.kind("leaf-1"),
        name = "Maple Leaf",
        quantity = 1,
        color = "red",
    })
end
""",
            )
            behave.add_behavior(
                "b:drop-branch:tick",
                lua="""
function(s, world, area, item)
    return area.make_here({
        kind = item.kind("branch-1"),
        name = "Maple Branch",
        quantity = 1,
    })
end
""",
            )
        return item


class LargeOakTree(Factory):
    def create(self, world: world.World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common("Large Oak Tree", desc="It's heavy."),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                "b:drop-leaf:tick",
                lua="""
function(s, world, area, item)
    return area.make_here({
        kind = item.kind("leaf-1"),
        name = "Oak Leaf",
        quantity = 1,
        color = "red",
    })
end
""",
            )
            behave.add_behavior(
                "b:drop-branch:tick",
                lua="""
function(s, world, area, item)
    return area.make_here({
        kind = item.kind("branch-1"),
        name = "Oak Branch",
        quantity = 1,
    })
end
""",
            )
        return item


class SmallCrevice:
    def create(self, world: world.World, generics: Generics, area: entity.Entity):
        item = scopes.exit(
            area=area,
            creator=world,
            parent=generics.thing,
            visible=mechanics.Visible(hard_to_see=True),
            props=properties.Common(
                "Small Crevice",
                desc="Whoa, how'd you even find this!?",
            ),
        )
        return item


class MysteriousBox(Factory):
    def create(self, world: world.World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common(
                "Mysterious Box",
                desc="It looks like some weird antique your grandmother would have. Why would anyone carry this thing around?",
            ),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                "b:mystery:shake",
                lua="""
function(s, world, area, item)
end
""",
            )
        return item


class LargeSteepCliff(Factory):
    def create(self, world: world.World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common(
                "Large Steep Cliff",
                desc="It's immense, with rocky outcroppings. It looks very climbable.",
            ),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                "b:make:stone",
                lua="""
function(s, world, area, item)
    if math.random() > 0.7 then
        return area.make_here({
            kind = item.kind("stone-1"),
            name = "Heavy Stone",
            quantity = 1,
        })
    end

    return area.make({
        kind = item.kind("pebble-1"),
        name = "Pebble",
        quantity = 3,
    })
end
""",
            )
        return item


class Guitar(Factory):
    def create(self, world: world.World, generics: Generics):
        item = scopes.item(
            creator=world,
            parent=generics.thing,
            props=properties.Common(
                "Acoustic Guitar", desc="Seems to be well travelled."
            ),
        )
        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                "b:music:play",
                lua="""
function(s, world, area, item)
end
""",
            )
        return item


class WoodenLadder:
    def create(self, world: world.World, generics: Generics, area: entity.Entity):
        item = scopes.exit(
            area=area,
            creator=world,
            parent=generics.thing,
            props=properties.Common("Wooden Ladder", desc="Seems sturdy enough."),
        )
        return item


class TomorrowCat(Factory):
    def create(self, world: world.World, generics: Generics):
        animal = scopes.alive(
            creator=world,
            parent=generics.thing,
            props=properties.Common(
                "Tomorrow", desc="She's a Maine Coon, and very elegant and pretty."
            ),
        )
        return animal


class CavernEntrance(Factory):
    def create(self, world: world.World, generics: Generics):
        area = scopes.exit(
            creator=world,
            parent=generics.area,
            props=properties.Common(
                "Entrance to a Dark Cavern",
                desc="It's dark, the cavern that is.",
            ),
        )
        return area


class DarkCavern(Factory):
    def create(self, world: world.World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=properties.Common(
                "Dark Cavern",
                desc="It's dark",
            ),
        )

        entrance = CavernEntrance().create(world, generics)

        add_item(
            area,
            scopes.exit(
                area=entrance,
                creator=world,
                parent=generics.thing,
                props=properties.Common(name=movement.Direction.NORTH.exiting),
            ),
        )

        return area


class ArtistsLoft(Factory):
    def create(self, world: world.World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=properties.Common(
                "Artist's Loft",
                desc="Everything is very colorful, because everything has got paint on it.",
            ),
        )
        return area


class RoomGrid(Factory):
    def __init__(self, w=1, h=1, **kwargs):
        super().__init__()
        self.w = w
        self.h = h

    def make_cell(self, world: world.World, generics: Generics, x, y):
        name = "Grid Room %d x %x" % (x, y)
        return scopes.area(
            creator=world,
            parent=generics.area,
            props=properties.Common(name, desc=name),
        )

    def create(self, world: world.World, generics: Generics):
        grid = [
            [self.make_cell(world, generics, y, x) for x in range(self.w)]
            for y in range(self.h)
        ]

        def add_doorway(from_cell, to_cell, direction):
            add_item(
                from_cell,
                scopes.exit(
                    area=to_cell,
                    creator=world,
                    parent=generics.thing,
                    props=properties.Common(name=direction.exiting),
                ),
            )

        def link_cells(cell1, cell2, direction):
            add_doorway(cell2, cell1)

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
    def create(self, world: world.World, generics: Generics):
        return RoomGrid(w=3, h=3).create(world, generics)


class MarbleSteps:
    def create(self, world: world.World, generics: Generics, area: entity.Entity):
        item = scopes.exit(
            area=area,
            creator=world,
            parent=generics.thing,
            props=properties.Common("Marble Steps", desc="Marble"),
        )
        return item


class NarrowCanyon:
    def create(self, world: world.World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=properties.Common(
                "Narrow Canyon",
                desc="It's barely wide enough to walk two by two down. The narrow walls really funnel the wind, creating powerful gusts.",
            ),
        )
        with area.make(mechanics.Weather) as weather:
            weather.wind = mechanics.Wind(magnitude=50)
        return area


class RockyPath:
    def create(self, world: world.World, generics: Generics, area: entity.Entity):
        item = scopes.exit(
            area=area,
            creator=world,
            parent=generics.thing,
            props=properties.Common("Rocky Path", desc="Looks easy enough"),
        )
        return item


class WelcomeArea(Factory):
    def create(self, world: world.World, generics: Generics):
        area = scopes.area(
            creator=world,
            parent=generics.area,
            props=properties.Common(
                "Town Courtyard.", desc="There's a ton going on here."
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
            props=properties.Common("A small clearing."),
        )
        add_item(
            area,
            scopes.exit(
                area=clearing,
                creator=world,
                parent=generics.thing,
                props=properties.Common("Worn Path"),
            ),
        )
        add_item(
            clearing,
            scopes.exit(
                area=area,
                creator=world,
                parent=generics.thing,
                props=properties.Common("Worn Path"),
            ),
        )

        add_item(clearing, LargeMapleTree().create(world, generics))

        cavern = DarkCavern().create(world, generics)
        add_item(clearing, SmallCrevice().create(world, generics, cavern))
        add_item(cavern, SmallCrevice().create(world, generics, clearing))

        museum = Museum().create(world, generics)
        add_item(clearing, MarbleSteps().create(world, generics, museum))
        add_item(museum, MarbleSteps().create(world, generics, clearing))

        return area


def create_example_world(world: world.World) -> Tuple[Generics, entity.Entity]:
    generics = Generics(world)
    area = WelcomeArea().create(world, generics)
    return generics, area
