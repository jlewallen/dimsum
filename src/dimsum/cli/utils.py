from typing import Tuple

import model.domains as domains

import storage


async def open_domain(path: str) -> domains.Domain:
    return domains.Domain(store=storage.SqliteStorage(path))
