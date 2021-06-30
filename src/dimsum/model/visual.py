from typing import List, Dict, Optional

import logging
import dataclasses

log = logging.getLogger("dimsum.visual")


class Renderable:
    def render_string(self) -> Dict[str, str]:
        raise NotImplementedError


@dataclasses.dataclass
class String(Renderable):
    message: str

    def render_string(self) -> Dict[str, str]:
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
