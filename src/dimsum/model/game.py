from typing import Optional

import dataclasses
import abc


class Reply:
    pass


class Action:
    def __init__(self, **kwargs):
        super().__init__()


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
