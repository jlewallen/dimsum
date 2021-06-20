import model.entity as entity


class EntityStorage:
    async def number_of_entities(self) -> int:
        raise NotImplementedError

    async def purge(self):
        raise NotImplementedError

    async def destroy(self, entity: entity.Entity):
        raise NotImplementedError

    async def update(self, entity: entity.Entity):
        raise NotImplementedError

    async def load_all(self, registrar: entity.Registrar):
        raise NotImplementedError

    async def load_entity_by_gid(self, registrar: entity.Registrar, gid: int):
        raise NotImplementedError

    async def load_entity_by_key(self, registrar: entity.Registrar, key: str):
        raise NotImplementedError


class SqliteStorage:
    pass


class HttpStorage:
    pass
