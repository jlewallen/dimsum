import dataclasses
from typing import Dict, List, Optional, Any

from loggers import get_logger
from model import Entity, Scope, event, StandardEvent, Acls, context


log = get_logger("dimsum.scopes")


@event
@dataclasses.dataclass(frozen=True)
class LivingEnteredArea(StandardEvent):
    def render_tree(self) -> Dict[str, Any]:
        return {"text": f"{self.source.props.name} arrived from {self.area}"}


@event
@dataclasses.dataclass(frozen=True)
class LivingLeftArea(StandardEvent):
    def render_tree(self) -> Dict[str, Any]:
        return {"text": f"{self.source.props.name} went to {self.area}"}


class Occupying(Scope):
    def __init__(self, area: Optional[Entity] = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area
        self.acls = Acls.owner_writes()

    def update(self, area: Entity):
        self.area = area
        self.ourselves.touch()


class Occupyable(Scope):
    def __init__(self, occupied=None, **kwargs):
        super().__init__(**kwargs)
        self.occupied: List[Entity] = occupied if occupied else []
        self.occupancy: int = 100
        self.acls = Acls.owner_writes()

    def add_living(self, living: Entity) -> Entity:
        assert isinstance(living, Entity)
        self.occupied.append(living)
        with living.make(Occupying) as occupying:
            occupying.update(self.ourselves)
            self.ourselves.touch()
        return living

    def occupying(self, living: Entity) -> bool:
        return living in self.occupied

    async def entered(self, player: Entity):
        assert player not in self.occupied
        await context.get().publish(
            LivingEnteredArea(source=player, area=self.ourselves, heard=self.occupied)
        )
        self.add_living(player)

    async def left(self, player: Entity):
        assert player in self.occupied
        self.occupied.remove(player)
        self.ourselves.touch()
        await context.get().publish(
            LivingLeftArea(source=player, area=self.ourselves, heard=self.occupied)
        )
