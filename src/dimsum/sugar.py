from typing import Any, Sequence, List, Dict
import logging
import behavior
import entity
import things
import envo
import world

log = logging.getLogger("dimsum")


@behavior.conditional(world.WindHook)
class WindBehavior(behavior.ConditionalBehavior):
    def enabled(self, entity: entity.Entity = None, **kwargs):
        if not isinstance(entity, envo.Area):  # HACK
            return False
        if entity.weather.wind is None:
            return False
        return True

    @property
    def lua(self):
        return """
function()
    debug("wind default")
end
"""