import dataclasses
import logging
from typing import Optional, List, Dict

from domains import Domain, Session

log = logging.getLogger("dimsum.cli")


@dataclasses.dataclass
class Migrator:
    domain: Domain

    async def migrate(self, session: Session):
        log.info("migrating")
        keys = await self.domain.store.load_all_keys()
        for key in keys:
            log.debug("migrating %s", key)
            await session.materialize(key=key)
        pass
