import logging
import game

log = logging.getLogger("dimsum")


class EventBus:
    async def publish(self, event: game.Event):
        log.info("publish:%s", event)
