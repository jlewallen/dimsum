import logging
import dataclasses
import abc
from typing import Dict, List, Any

log = logging.getLogger("dimsum.visual")


class Renderable:
    def render_tree(self) -> Dict[str, Any]:
        return {"unimplemented": True}


@dataclasses.dataclass
class String(Renderable):
    message: str

    def render_tree(self) -> Dict[str, Any]:
        return {"message": self.message}


class Comms:
    async def somebody(self, key: str, r: Renderable) -> bool:
        raise NotImplementedError

    async def everybody(self, r: Renderable) -> bool:
        raise NotImplementedError


class NoopComms(Comms):
    async def somebody(self, key: str, r: Renderable) -> bool:
        log.info("noop-comms: somebody=%s", key)
        return True

    async def everybody(self, r: Renderable) -> bool:
        log.info("noop-comms: everybody")
        return True


@dataclasses.dataclass
class Updated(Renderable):
    entities: List[Dict[str, Any]]
    information: bool = True
