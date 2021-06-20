from typing import Tuple

import model.domains as domains

import luaproxy
import handlers
import messages
import persistence


async def open_domain(path: str) -> domains.Domain:
    domain = domains.Domain(storage=persistence.SqliteDatabase())
    await domain.storage.open(path)
    await domain.storage.load_all(domain.registrar)
    return domain
