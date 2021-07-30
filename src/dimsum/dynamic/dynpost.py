import dataclasses
from datetime import datetime

from model import Entity, Event
import scopes.inbox as inbox


@dataclasses.dataclass
class DynamicPostService:
    postService: inbox.PostService

    async def future(self, when: datetime, receiver: Entity, message: Event):
        return await self.postService.future(when, receiver, message)
