import props
import game
import actions


class Factory:
    def create(self, world: game.World):
        raise Exception("unimplemented")


class Hammer(Factory):
    def create(self, world: game.World):
        return game.Item(
            creator=world,
            details=props.Details("Hammer", desc="It's heavy."),
        )


class LargeOakTree(Factory):
    def create(self, world: game.World):
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


class WelcomeArea(Factory):
    def create(self, world: game.World):
        area = game.Area(
            creator=world,
            details=props.Details("Living room", desc="It's got walls."),
        )
        area.add_item(LargeOakTree().create(world))
        area.add_item(Hammer().create(world))
        return area


def create_example_world(world: game.World) -> game.Area:
    return WelcomeArea().create(world)
