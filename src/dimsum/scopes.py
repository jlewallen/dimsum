import ownership
import health
import mechanics

Alive = [ownership.Ownership, health.HealthMixin, mechanics.MemoryMixin]
Item = [ownership.Ownership, health.EdibleMixin]
Area = [ownership.Ownership]
World = [ownership.Ownership]
