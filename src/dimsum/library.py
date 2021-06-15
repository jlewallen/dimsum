import logging
import properties
import game
import world
import things
import envo
import animals
import actions
import movement
import mechanics

log = logging.getLogger("dimsum")


class Factory:
    def create(self, world: world.World):
        raise NotImplementedError


class Hammer(Factory):
    def create(self, world: world.World):
        return things.Item(
            creator=world,
            props=properties.Common("Hammer", desc="It's heavy."),
        )


class BeerKeg(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common("Beer Keg", desc="It's heavy."),
        )
        return item


class LargeMapleTree(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common("Large Maple Tree", desc="It's heavy."),
        )
        item.add_behavior(
            "b:drop-leaf:tick",
            lua="""
function(s, world, area, item)
    return area.make({
        kind = item.kind("leaf-1"),
        name = "Maple Leaf",
        quantity = 1,
        color = "red",
    })
end
""",
        )
        item.add_behavior(
            "b:drop-branch:tick",
            lua="""
function(s, world, area, item)
    return area.make({
        kind = item.kind("branch-1"),
        name = "Maple Branch",
        quantity = 1,
    })
end
""",
        )
        return item


class LargeOakTree(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common("Large Oak Tree", desc="It's heavy."),
        )
        item.add_behavior(
            "b:drop-leaf:tick",
            lua="""
function(s, world, area, item)
    return area.make({
        kind = item.kind("leaf-1"),
        name = "Oak Leaf",
        quantity = 1,
        color = "red",
    })
end
""",
        )
        item.add_behavior(
            "b:drop-branch:tick",
            lua="""
function(s, world, area, item)
    return area.make({
        kind = item.kind("branch-1"),
        name = "Oak Branch",
        quantity = 1,
    })
end
""",
        )
        return item


class SmallCrevice(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            visible=mechanics.Visible(hard_to_see=True),
            props=properties.Common(
                "Small Crevice",
                desc="Whoa, how'd you even find this!?",
            ),
        )
        return item


class MysteriousBox(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common(
                "Mysterious Box",
                desc="It looks like some weird antique your grandmother would have. Why would anyone carry this thing around?",
            ),
        )
        item.add_behavior(
            "b:mystery:shake",
            lua="""
function(s, world, area, item)
end
""",
        )
        return item


class LargeSteepCliff(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common(
                "Large Steep Cliff",
                desc="It's immense, with rocky outcroppings. It looks very climbable.",
            ),
        )
        item.add_behavior(
            "b:make:stone",
            lua="""
function(s, world, area, item)
    if math.random() > 0.7 then
        return area.make({
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
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common(
                "Acoustic Guitar", desc="Seems to be well travelled."
            ),
        )
        item.add_behavior(
            "b:music:play",
            lua="""
function(s, world, area, item)
end
""",
        )
        return item


class WoodenLadder(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common("Wooden Ladder", desc="Seems sturdy enough."),
        )
        return item


class TomorrowCat(Factory):
    def create(self, world: world.World):
        animal = animals.Animal(
            creator=world,
            props=properties.Common(
                "Tomorrow", desc="She's a Maine Coon, and very elegant and pretty."
            ),
        )
        return animal


class CavernEntrance(Factory):
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
            props=properties.Common(
                "Entrance to a Dark Cavern",
                desc="It's dark, the cavern that is.",
            ),
        )
        return area


class DarkCavern(Factory):
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
            props=properties.Common(
                "Dark Cavern",
                desc="It's dark",
            ),
        )

        entrance = CavernEntrance().create(world)

        area.add_route(
            movement.DirectionalRoute(direction=movement.Direction.NORTH, area=entrance)
        )

        return area


class ArtistsLoft(Factory):
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
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

    def make_cell(self, world: world.World, x, y):
        name = "Grid Room %d x %x" % (x, y)
        return envo.Area(
            creator=world,
            props=properties.Common(name, desc=name),
        )

    def create(self, world: world.World):
        grid = [
            [self.make_cell(world, y, x) for x in range(self.w)] for y in range(self.h)
        ]

        def add_doorway(from_cell, to_cell, direction):
            from_cell.add_route(
                movement.DirectionalRoute(direction=direction, area=to_cell)
            )

        def link_cells(cell1, cell2, direction):
            add_doorway(cell2, cell1)

        def try_add(cell, ox, oy, x, y, direction):
            if y < 0 or y >= len(grid):
                return
            row = grid[y]
            if x < 0 or x >= len(row):
                return
            # print("linking (%d, %d) -> (%d, %d) %s" % (ox, oy, x, y, direction))
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
    def create(self, world: world.World):
        return RoomGrid(w=3, h=3).create(world)


class MarbleSteps(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common("Marble Steps", desc="Marble"),
        )
        return item


class AddItemRoute:
    def __init__(self, world=None, **kwargs):
        assert world
        self.world = world
        self.kwargs = kwargs

    def area(self, **kwargs):
        self.area = envo.Area(creator=self.world, **kwargs)
        return self

    def via(self, **kwargs):
        self.item = things.Item(creator=self.world, **kwargs)
        self.item.link_area(self.area)
        return self.item


class NarrowCanyon:
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
            props=properties.Common(
                "Narrow Canyon",
                desc="It's barely wide enough to walk two by two down. The narrow walls really funnel the wind, creating powerful gusts.",
            ),
        )
        area.add_weather(mechanics.Weather(wind=mechanics.Wind(magnitude=50)))
        return area


class RockyPath:
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            props=properties.Common("Rocky Path", desc="Looks easy enough"),
        )
        return item


class WelcomeArea(Factory):
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
            props=properties.Common(
                "Town Courtyard.", desc="There's a ton going on here."
            ),
        )
        area.add_item(BeerKeg().create(world))
        area.add_item(LargeOakTree().create(world))
        area.add_item(Hammer().create(world))
        area.add_item(MysteriousBox().create(world))
        area.add_item(Guitar().create(world))
        area.add_item(LargeSteepCliff().create(world))
        area.add_living(TomorrowCat().create(world))

        loft = ArtistsLoft().create(world)
        ladder = WoodenLadder().create(world)
        ladder.link_area(loft)
        area.add_item_and_link_back(ladder)

        canyon = NarrowCanyon().create(world)
        rocky_path = RockyPath().create(world)
        rocky_path.link_area(canyon)
        area.add_item_and_link_back(rocky_path)

        _, clearing = area.add_item_and_link_back(
            AddItemRoute(world)
            .area(props=properties.Common("A small clearing."))
            .via(props=properties.Common("Worn Path"))
        )

        clearing.add_item(LargeMapleTree().create(world))

        cavern = DarkCavern().create(world)
        crevice = SmallCrevice().create(world)
        crevice.link_area(cavern)
        clearing.add_item(crevice)

        museum = Museum().create(world)
        steps = MarbleSteps().create(world)
        steps.link_area(museum)
        clearing.add_item_and_link_back(steps)

        return area


def create_example_world(world: world.World) -> envo.Area:
    return WelcomeArea().create(world)
