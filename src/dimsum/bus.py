from typing import Union, Any
import logging

log = logging.getLogger("dimsum")


class EventBus:
    async def publish(self, event: Union[Any]):
        log.info("publish:%s", event)
