from typing import Tuple

import model.domains as domains

import luaproxy
import handlers
import messages
import storage


async def open_domain(path: str) -> domains.Domain:
    domain = domains.Domain(store=storage.SqliteStorage(path))
    await domain.load()
    return domain
