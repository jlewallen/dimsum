import logging
import bus
import events

from context import *
from reply import *
from game import *
from things import *
from envo import *
from living import *
from animals import *
from events import *
from world import *

log = logging.getLogger("dimsum")


class TextBus(bus.EventBus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def publish(self, event: events.Event, **kwargs):
        assert event
        log.info("publish:%s", event)
        self.invoke_handlers(event)
        message = await event.accept(self)
        log.info("text:%s", message)
        return None

    async def ItemsMade(self, person=None, items=None, **kwargs):
        return "%s created %s out of thin air!" % (person, items)

    async def LivingEnteredArea(self, person=None, area=None, **kwargs):
        return "%s entered %s" % (person, area)

    async def LivingLeftArea(self, person=None, area=None, **kwargs):
        return "%s left %s" % (person, area)

    async def PlayerJoined(self, player: Player=None, area=None, **kwargs):
        return "%s joined!" % (player)

    async def ItemHeld(self, person=None, area=None, items=None, **kwargs):
        return "%s held %s" % (person, items)

    async def ItemsDropped(self, person=None, area=None, items=None, **kwargs):
        return "%s dropped %s" % (person, items)

    async def ItemObliterated(self, person=None, area=None, items=None, **kwargs):
        return "%s obliterated %s" % (person, items)

    async def ItemDrank(self, person=None, area=None, item=None, **kwargs):
        return "%s drank %s" % (person, item)

    async def ItemEaten(self, person=None, area=None, item=None, **kwargs):
        return "%s ae %s" % (person, item)

    async def ItemsAppeared(self, area=None, item=None, **kwargs):
        return "%s suddenly appeared!" % (item)
