import functools
import copy
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from loggers import get_logger
from model import EntityRef, CompiledJson
from domains import Domain, Session
from serializing import PyObjectKey, PyRefKey, full_class_name

log = get_logger("dimsum.cli")


@dataclass
class MigrateContext:
    dirty: bool = False

    def touch(self):
        self.dirty = True


@functools.singledispatch
def _migrate(incoming: Any, ctx: MigrateContext) -> Dict[str, Any]:
    return incoming


@_migrate.register
def _migrate_list(value: list, ctx: MigrateContext):
    return [_migrate(v, ctx) for v in value]


_object_names = {
    "serializing.RootEntity": "model.entity.Entity",
    "serializing.RootWorld": "model.world.World",
}


@_migrate.register
def _migrate_dict(value: dict, ctx: MigrateContext):
    migrated = copy.copy(value)
    if PyObjectKey in value:
        pyObject = value[PyObjectKey]
        if pyObject in _object_names and "scopes" in value:
            migrated[PyObjectKey] = _object_names[pyObject]
            ctx.touch()
        if "name" in value and "klass" in value and "key" in value:
            if PyRefKey in migrated:
                pass
            else:
                migrated[PyRefKey] = pyObject
                migrated[PyObjectKey] = full_class_name(EntityRef)
                ctx.touch()
    return {key: _migrate(v, ctx) for key, v in migrated.items()}


def migrate(compiled: CompiledJson) -> Tuple[bool, CompiledJson]:
    ctx = MigrateContext()
    migrated = _migrate(compiled.compiled, ctx)
    if ctx.dirty:
        return True, CompiledJson(json.dumps(migrated), migrated)
    return False, compiled


@dataclass
class Migrator:
    domain: Domain

    async def migrate(self, session: Session):
        log.info("migrating")
        keys = await self.domain.store.load_all_keys()
        for key in keys:
            log.debug("migrating %s", key)
            try:
                await session.materialize(key=key, migrate=migrate)
            except:
                log.exception("migrate:error: %s", key, exc_info=True)
                raise
