from typing import Any, Sequence, List, Dict
import logging
import behavior
import entity
import things
import envo

log = logging.getLogger("dimsum")


@behavior.conditional
class WindBehavior(behavior.ConditionalBehavior):
    def enabled(self, entity: entity.Entity = None, **kwargs):
        if not isinstance(entity, envo.Area):  # HACK
            return False
        if entity.weather.wind is None:
            return False
        return True

    @property
    def name(self):
        return "wind"

    @property
    def lua(self):
        return """
function()
    debug("wind default")
end
"""
