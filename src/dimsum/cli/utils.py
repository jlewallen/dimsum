import domains
import storage


async def open_domain(path: str) -> domains.Domain:
    return domains.Domain(store=storage.SqliteStorage(path))
