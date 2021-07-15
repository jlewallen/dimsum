import domains
import storage


async def open_domain(path: str, read_only=False) -> domains.Domain:
    return domains.Domain(store=storage.SqliteStorage(path, read_only=read_only))
