import logging
from typing import Optional

import bus
from model import Comms, Renderable, StandardEvent
from saying import DynamicMessage

log = logging.getLogger("dimsum.handlers")


class EventHandlers(bus.TextRendering):
    def install(self, bus: bus.EventBus, comms: Comms):
        @bus.handler(DynamicMessage)
        async def handle_dynamic_message(
            event: Optional[DynamicMessage] = None, **kwargs
        ):
            assert event
            log.info("%s: event=%s kwargs=%s", type(event), event, kwargs)
            if event.heard:
                for nearby in event.heard:
                    await comms.somebody(nearby.key, event)

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
