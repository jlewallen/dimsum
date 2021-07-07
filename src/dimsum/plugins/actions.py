import context
import model.entity as entity
import model.game as game
import model.world as world


class PersonAction(game.Action):
    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ) -> game.Reply:
        raise NotImplementedError
