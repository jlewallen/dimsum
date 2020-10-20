import props
import game
import world
import things
import envo
import animals
import actions
import movement


class Factory:
    def create(self, world: world.World):
        raise Exception("unimplemented")


class Hammer(Factory):
    def create(self, world: world.World):
        return things.Item(
            creator=world,
            details=props.Details("Hammer", desc="It's heavy."),
        )


class BeerKeg(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            details=props.Details("Beer Keg", desc="It's heavy."),
        )
        return item


class LargeOakTree(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            details=props.Details("Large Oak Tree", desc="It's heavy."),
        )
        item.add_behavior(
            "b:growing:tick",
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
        return item


class MysteriousBox(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            details=props.Details(
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


class Guitar(Factory):
    def create(self, world: world.World):
        item = things.Item(
            creator=world,
            details=props.Details(
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
            details=props.Details("Wooden Ladder", desc="Seems sturdy enough."),
        )
        return item


class TomorrowCat(Factory):
    def create(self, world: world.World):
        animal = animals.Animal(
            creator=world,
            details=props.Details(
                "Tomorrow", desc="She's a Maine Coon, and very elegant and pretty."
            ),
        )
        return animal


class ArtistsLoft(Factory):
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
            details=props.Details(
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
            details=props.Details(name, desc=name),
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
            details=props.Details("Marble Steps", desc="Marble"),
        )
        return item


class WelcomeArea(Factory):
    def create(self, world: world.World):
        area = envo.Area(
            creator=world,
            details=props.Details("Living room", desc="It's got walls."),
        )
        area.add_item(BeerKeg().create(world))
        area.add_item(LargeOakTree().create(world))
        area.add_item(Hammer().create(world))
        area.add_item(MysteriousBox().create(world))
        area.add_item(Guitar().create(world))
        area.add_living(TomorrowCat().create(world))

        museum = Museum().create(world)
        steps = MarbleSteps().create(world)
        steps.link_area(museum)
        area.add_item(steps)

        loft = ArtistsLoft().create(world)
        ladder = WoodenLadder().create(world)
        ladder.link_area(loft)
        area.add_item(ladder)
        return area


def create_example_world(world: world.World) -> envo.Area:
    return WelcomeArea().create(world)
