import ownership
import health
import mechanics
import occupyable

Alive = [ownership.Ownership, health.HealthMixin, mechanics.MemoryMixin]
Item = [ownership.Ownership, health.EdibleMixin]
Area = [ownership.Ownership, occupyable.OccupyableMixin]
World = [ownership.Ownership]
