from typing import Dict, Any, List, Optional

import copy
import jsonpickle
import wrapt
import logging

import model.crypto as crypto
import model.entity as entity
import model.world as world

import model.scopes.movement as movement

import storage

log = logging.getLogger("dimsum")


@jsonpickle.handlers.register(crypto.Identity, base=True)
class IdentityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return crypto.Identity(
            public=obj["public"], private=obj["private"], signature=obj["signature"]
        )

    def flatten(self, obj, data):
        if self.context.reproducible:
            data["public"] = "<public>"
            data["signature"] = "<signature>"
            data["private"] = "<private>"
            return

        data["public"] = obj.public
        data["signature"] = obj.signature
        if self.context.secure:
            data["private"] = obj.private
        return data


@jsonpickle.handlers.register(movement.Direction)
class DirectionHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        if "compass" in obj:
            name = obj["compass"].lower()
            for d in movement.Direction:
                if name == d.name.lower():
                    return d
        return None

    def flatten(self, obj, data):
        data["compass"] = obj.name
        return data


@jsonpickle.handlers.register(entity.Entity)
@jsonpickle.handlers.register(world.World)
class EntityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return self.context.lookup(obj["key"])

    def flatten(self, obj, data):
        data["key"] = obj.key
        data["klass"] = obj.klass.__name__
        data["name"] = obj.props.name
        return data


class SecurePickler(jsonpickle.pickler.Pickler):
    def __init__(self, secure=False, reproducible=False, **kwargs):
        super().__init__(**kwargs)
        self.secure = secure
        self.reproducible = reproducible


class CustomUnpickler(jsonpickle.unpickler.Unpickler):
    def __init__(self, lookup, **kwargs):
        super().__init__()
        self.lookup = lookup


def derive_from(klass):
    name = klass.__name__
    return type("Root" + name, (klass,), {})


allowed = [
    entity.Entity,
    world.World,
]
classes = {k: derive_from(k) for k in allowed}
inverted = {v: k for k, v in classes.items()}


def serialize_full(value, depth=0):
    if isinstance(value, list):
        value = [serialize_full(item, depth=depth + 1) for item in value]

    if isinstance(value, dict):
        value = {
            key: serialize_full(value, depth=depth + 1) for key, value in value.items()
        }

    if value.__class__ in classes:
        log.debug(
            "swap class: %s -> %s (%s)", type(value), classes[value.__class__], value
        )
        attrs = copy.copy(value.__dict__)
        if "hooks" in attrs:
            del attrs["hooks"]
        klass = classes[value.__class__]
        return klass(**attrs)
    return value


def serialize(
    value, indent=None, unpicklable=True, secure=False, full=True, reproducible=False
):
    if value is None:
        return value

    prepared = serialize_full(value) if full else value

    return jsonpickle.encode(
        prepared,
        indent=indent,
        unpicklable=unpicklable,
        make_refs=False,
        context=SecurePickler(
            secure=secure,
            unpicklable=unpicklable,
            reproducible=reproducible,
            make_refs=False,
        ),
    )


def deserialize(encoded, lookup):
    decoded = jsonpickle.decode(
        encoded,
        context=CustomUnpickler(lookup),
        classes=list(classes.values()),
    )

    if type(decoded) in inverted:
        original = inverted[type(decoded)]
        return original(**decoded.__dict__)

    return decoded


async def materialize_json(
    data: str,
    registrar: entity.Registrar,
    store: storage.EntityStorage,
    depth: int = 0,
) -> Optional[entity.Entity]:
    log.info("[%d] materialize", depth)

    refs: Dict[str, entity.EntityRef] = {}

    def reference(key):
        if registrar.contains(key):
            return registrar.find_by_key(key)

        if key not in refs:
            refs[key] = entity.EntityRef(key)
        return refs[key]

    loaded = deserialize(data, reference)
    assert loaded
    registrar.register(loaded)

    for referenced_key, proxy in refs.items():
        linked = await materialize(referenced_key, registrar, store, depth=depth + 1)
        proxy.__wrapped__ = linked  # type: ignore

    loaded.validate()

    return loaded


async def materialize(
    key: str,
    registrar: entity.Registrar,
    store: storage.EntityStorage,
    depth: int = 0,
) -> Optional[entity.Entity]:
    log.info("[%d] materialize %s", depth, key)

    if registrar.contains(key):
        log.debug("[%d] return fbk", depth)
        return registrar.find_by_key(key)

    data = await store.load_by_key(key)
    if data is None:
        log.info("[%d] %s missing %s", depth, store, key)
        return None

    return await materialize_json(data, registrar=registrar, store=store, depth=depth)


def maybe_destroyed(e: entity.Entity) -> Optional[entity.Entity]:
    if e.props.destroyed:
        log.info("destroyed: %s", e)
        return None
    return e


def registrar(
    registrar: entity.Registrar, **kwargs
) -> Dict[storage.Keys, Optional[str]]:
    return {
        storage.Keys(key=entity.key, gid=entity.props.gid): serialize(
            maybe_destroyed(entity), secure=True, **kwargs
        )
        for key, entity in registrar.entities.items()
    }


def for_update(entities: List[entity.Entity], **kwargs) -> Dict[storage.Keys, str]:
    return {
        storage.Keys(key=entity.key, gid=entity.props.gid): serialize(
            entity, secure=True, **kwargs
        )
        for entity in entities
    }
