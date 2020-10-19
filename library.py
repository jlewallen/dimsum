import props
import game
import world
import actions


class Factory:
    def create(self, world: world.World):
        raise Exception("unimplemented")


class Hammer(Factory):
    def create(self, world: world.World):
        return game.Item(
            creator=world,
            details=props.Details("Hammer", desc="It's heavy."),
        )


class BeerKeg(Factory):
    def create(self, world: world.World):
        item = game.Item(
            creator=world,
            details=props.Details("Beer Keg", desc="It's heavy."),
        )
        return item


class LargeOakTree(Factory):
    def create(self, world: world.World):
        item = game.Item(
            creator=world,
            details=props.Details("Large Oak Tree", desc="It's heavy."),
        )
        item.add_behavior(
            "b:growing:tick",
            lua="""
function(s, world, area, item)
    return area.make({
        kind = item.kind("leaves-1"),
        name = "Oak Leaves",
        quantity = 1,
        color = "red",
    })
end
""",
        )
        return item


class TomorrowCat(Factory):
    def create(self, world: world.World):
        animal = game.Animal(
            creator=world,
            details=props.Details(
                "Tomorrow", desc="She's a Maine Coon, and very elegant and pretty."
            ),
        )
        return animal


class WelcomeArea(Factory):
    def create(self, world: world.World):
        area = game.Area(
            creator=world,
            details=props.Details("Living room", desc="It's got walls."),
        )
        area.add_item(BeerKeg().create(world))
        area.add_item(LargeOakTree().create(world))
        area.add_item(Hammer().create(world))
        area.add_living(TomorrowCat().create(world))
        return area


def create_example_world(world: world.World) -> game.Area:
    return WelcomeArea().create(world)
