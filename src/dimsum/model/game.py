import dataclasses
import logging
from typing import Optional


class Reply:
    pass


class Action:
    def __init__(self, **kwargs):
        super().__init__()


class Unknown(Action):
    async def perform(self, **kwargs):
        return Failure("sorry, i don't understand")


@dataclasses.dataclass
class DynamicFailure:
    exception: str
    handler: str


@dataclasses.dataclass(frozen=True)
class SimpleReply(Reply):
    message: Optional[str] = None


class Success(SimpleReply):
    def __str__(self):
        if self.message:
            return "Success<%s>" % (self.message,)
        return "Success"


class Failure(SimpleReply):
    def __str__(self):
        if self.message:
            return "Failure<%s>" % (self.message,)
        return "Failure"
