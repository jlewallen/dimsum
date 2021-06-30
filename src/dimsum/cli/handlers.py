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


class EventHandlers:
    def __init__(self, bus: bus.EventBus, comms: visual.Comms):
        self.comms = comms

        @bus.handler(Event)
        async def handle_plain_event(event, **kwargs):
            log.debug("event: %s %s", event, kwargs)

        @bus.handler(PlayerJoined)
        async def handle_player_joined(player: entity.Entity = None, **kwargs):
            log.info("player joined handler: %s %s", player, kwargs)

        @bus.handler(StandardEvent)
        async def handle_standard_event(
            person: entity.Entity = None,
            heard: List[entity.Entity] = None,
            event: StandardEvent = None,
            **kwargs
        ):
            assert event
            log.info(
                "%s: person=%s heard=%s kwargs=%s", type(event), person, heard, kwargs
            )
            if heard:
                for nearby in heard:
                    await self.comms.somebody(nearby.key, event)


def create(comms: visual.Comms):
    def factory(bus):
        return EventHandlers(bus, comms)

    return factory
