import functools
from typing import Optional

import bus
from loggers import get_logger
from model import Comms, Renderable, StandardEvent
from saying import DynamicMessage

log = get_logger("dimsum.handlers")


class EventHandlers:
    def __init__(self, comms: Comms, bus: bus.EventBus):
        @bus.handler(DynamicMessage)
        async def handle_dynamic_message(
            event: Optional[DynamicMessage] = None, **kwargs
        ):
            assert event
            log.debug("event: %s kwargs=%s", event, kwargs)
            if event.heard:
                for nearby in event.heard:
                    await comms.somebody(nearby.key, event)

        @bus.handler(StandardEvent)
        async def handle_standard_event(
            event: Optional[StandardEvent] = None, **kwargs
        ):
            assert event
            log.debug("event: %s kwargs=%s", event, kwargs)
            if event.heard:
                for nearby in event.heard:
                    await comms.somebody(nearby.key, event)


def create(comms: Comms):
    return functools.partial(EventHandlers, comms)
