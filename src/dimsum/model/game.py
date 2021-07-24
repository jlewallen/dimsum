import dataclasses
from typing import List, Optional


class Reply:
    pass


class Universal(Reply):
    def __init__(self, f: str, ok: Optional[bool] = True, **kwargs):
        super().__init__()
        self.f = f
        self.kwargs = kwargs
        self.ok = ok

    def failed(self) -> "Universal":
        return self

    def __str__(self) -> str:
        return self.f % self.kwargs


class Action:
    def __init__(self, **kwargs):
        super().__init__()

    def gather_roles(self) -> List[str]:
        return []


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
