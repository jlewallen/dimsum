import logging
import dataclasses
from typing import Optional


class Reply:
    pass


class Universal(Reply):
    def __init__(self, *args, ok: Optional[bool] = True, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.ok = ok

    def failed(self) -> "Universal":
        return self


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
    pass


class Failure(SimpleReply):
    pass
