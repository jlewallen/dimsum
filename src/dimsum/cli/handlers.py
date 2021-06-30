from typing import Any, List

import os
import hashlib
import base64

import bus
import context

import model.entity as entity
import model.visual as visual

from model.events import *

import model.scopes.movement as movement
import model.scopes.health as health

log = logging.getLogger("dimsum.handlers")


class EventHandlers(bus.TextRendering):
    def install(self, bus: bus.EventBus, comms: visual.Comms):
        @bus.handler(StandardEvent)
        async def handle_standard_event(event: StandardEvent = None, **kwargs):
            assert event
            log.info("%s: event=%s kwargs=%s", type(event), event, kwargs)
            if event.heard:
                for nearby in event.heard:
                    await comms.somebody(nearby.key, event)


def create(comms: visual.Comms):
    def factory(bus):
        return EventHandlers(bus, comms)

    return factory
