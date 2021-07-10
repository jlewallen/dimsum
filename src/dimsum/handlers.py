import logging
from typing import Optional

import bus
from model import Comms, Renderable, StandardEvent

log = logging.getLogger("dimsum.handlers")


class EventHandlers(bus.TextRendering):
    def install(self, bus: bus.EventBus, comms: Comms):
        @bus.handler(StandardEvent)
        async def handle_standard_event(
            event: Optional[StandardEvent] = None, **kwargs
        ):
            assert event
            log.info("%s: event=%s kwargs=%s", type(event), event, kwargs)
            if event.heard:
                for nearby in event.heard:
                    await comms.somebody(nearby.key, event)


def create(comms: Comms):
    def factory(bus):
        return EventHandlers(bus, comms)

    return factory
