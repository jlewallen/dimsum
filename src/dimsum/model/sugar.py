from typing import Any, Sequence, List, Dict
import logging

import model.entity as entity
import model.world as world

import model.scopes.behavior as behavior
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable

log = logging.getLogger("dimsum")


@behavior.conditional(world.WindHook)
class WindBehavior(behavior.ConditionalBehavior):
    def enabled(self, entity: entity.Entity = None, **kwargs):
        assert entity
        if entity.has(occupyable.Occupyable):
            log.info("occupyable: %s", entity)
            with entity.make(mechanics.Weather) as weather:
                if weather.wind:
                    return True
        return False

    @property
    def lua(self):
        return """
function()
    debug("wind default")
end
"""
