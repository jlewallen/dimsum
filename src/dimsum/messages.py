import logging
import bus
import events
import inflect

from context import *
from reply import *
from game import *
from things import *
from living import *
from events import *
from world import *

log = logging.getLogger("dimsum")
p = inflect.engine()


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

    async def LivingEnteredArea(self, living=None, area=None, **kwargs):
        return "%s entered %s" % (living, area)

    async def LivingLeftArea(self, living=None, area=None, **kwargs):
        return "%s left %s" % (living, area)

    async def PlayerJoined(self, player: entity.Entity = None, area=None, **kwargs):
        return "%s joined!" % (player)

    async def ItemHeld(self, person=None, area=None, items=None, **kwargs):
        return "%s held %s" % (
            person,
            p.join(
                items,
            ),
        )

    async def ItemsDropped(self, person=None, area=None, items=None, **kwargs):
        return "%s dropped %s" % (
            person,
            p.join(
                items,
            ),
        )

    async def ItemObliterated(self, person=None, area=None, items=None, **kwargs):
        return "%s obliterated %s" % (
            person,
            p.join(
                items,
            ),
        )

    async def ItemDrank(self, person=None, area=None, item=None, **kwargs):
        return "%s drank %s" % (person, item)

    async def ItemEaten(self, person=None, area=None, item=None, **kwargs):
        return "%s ae %s" % (person, item)

    async def ItemsAppeared(self, area=None, items=None, **kwargs):
        return "%s suddenly appeared!" % (p.join(items),)


class EmbedObservationVisitor:
    def personal_observation(self, obs):
        emd = obs.props.desc
        emd += "\n"

        emd += "Properties:\n"
        for key, value in obs.properties.items():
            emd += key + "=" + str(value) + "\n"
        emd += "\n"

        emd += "Memory:\n"
        for key, value in obs.memory.items():
            emd += key + "=" + str(value) + "\n"
        emd += "\n"

        return {"title": obs.props.name, "description": emd}

    def detailed_observation(self, obs):
        emd = obs.props.desc
        emd += "\n"
        for key, value in obs.properties.items():
            emd += "\n" + key + "=" + str(value)
        for key, value in obs.what.behaviors.items():
            emd += "\n" + key + "=" + value.lua
        return {"title": obs.props.name, "description": emd}

    def area_observation(self, obs):
        emd = obs.props.desc
        emd += "\n\n"
        if len(obs.living) > 0:
            emd += "Also here: " + p.join([str(x) for x in obs.living])
            emd += "\n"
        if len(obs.items) > 0:
            emd += "You can see " + p.join([str(x) for x in obs.items])
            emd += "\n"
        if len(obs.who.holding) > 0:
            emd += "You're holding " + p.join([str(x) for x in obs.who.holding])
            emd += "\n"
        directional = [
            e for e in obs.routes if isinstance(e, movement.DirectionalRoute)
        ]
        if len(directional) > 0:
            directions = [d.direction for d in directional]
            emd += "You can go " + p.join([str(d) for d in directions])
            emd += "\n"
        return {"title": obs.props.name, "description": emd}

    def item(self, item):
        return str(item)

    def observed_person(self, observed):
        return observed.person.accept(self)

    def observed_entity(self, observed):
        return observed.entity.accept(self)

    def observed_entities(self, observed):
        return [e.accept(self) for e in observed.entities]

    def entities_observation(self, obs):
        if len(obs.entities) == 0:
            return {"text": "nothing"}
        return {"text": p.join([str(x) for x in obs.entities])}


class ReplyVisitor(EmbedObservationVisitor):
    def failure(self, reply):
        return {"text": reply.message}

    def success(self, reply):
        return {"text": reply.message}
