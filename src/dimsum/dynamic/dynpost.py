import dataclasses
from datetime import datetime

from model import Entity
import scopes.inbox as inbox


@dataclasses.dataclass
class DynamicPostMessage(inbox.PostMessage):
    message: inbox.PostMessage


@dataclasses.dataclass
class DynamicPostService:
    postService: inbox.PostService

    async def future(
        self, receiver: Entity, when: datetime, message: inbox.PostMessage
    ):
        return await self.postService.future(
            receiver, when, DynamicPostMessage(message)
        )
