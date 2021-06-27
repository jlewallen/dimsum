from typing import Dict, Any, List, Optional, Union

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


entity_types = {"model.entity.Entity": entity.Entity, "model.world.World": world.World}


# From stackoverflow
def fullname(klass):
    module = klass.__module__
    if module == "builtins":
        return klass.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + klass.__qualname__


@jsonpickle.handlers.register(entity.EntityRef)
class EntityRefHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        raise NotImplementedError

    def flatten(self, obj, data):
        assert obj.pyObject
        data["py/object"] = fullname(obj.pyObject)
        data["key"] = obj.key
        data["klass"] = obj.klass
        data["name"] = obj.name
        return data


@jsonpickle.handlers.register(entity.Entity)
@jsonpickle.handlers.register(world.World)
class EntityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        pyObject = entity_types[obj["py/object"]]
        ref = entity.EntityRef.new(pyObject=pyObject, **obj)
        log.debug("entity-handler: %s", ref)
        return self.context.lookup(ref)

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


class SerializationException(Exception):
    pass


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


async def materialize(
    registrar: entity.Registrar = None,
    store: storage.EntityStorage = None,
    key: str = None,
    gid: int = None,
    json: List[entity.Serialized] = None,
    reach=None,
    depth: int = 0,
    cache: Dict[str, List[entity.Serialized]] = None,
) -> Union[Optional[entity.Entity], List[entity.Entity]]:
    assert registrar
    assert store

    single_entity = json is None
    cache = cache or {}
    found = None
    if key is not None:
        log.debug("[%d] materialize key=%s", depth, key)
        found = registrar.find_by_key(key)
        if found:
            return found

        if key in cache:
            json = cache[key]
        else:
            json = await store.load_by_key(key)
            if len(json) == 0:
                log.info("[%d] %s missing key=%s", depth, store, key)
                return None

    if gid is not None:
        log.debug("[%d] materialize gid=%d", depth, gid)
        found = registrar.find_by_gid(gid)
        if found:
            return found

        json = await store.load_by_gid(gid)
        if len(json) == 0:
            log.info("[%d] %s missing gid=%d", depth, store, gid)
            return None

    log.debug("json: %s", json)

    refs: Dict[str, entity.EntityProxy] = {}

    def reference(ref: entity.EntityRef):
        assert registrar
        if registrar.contains(ref.key):
            return registrar.find_by_key(ref.key)

        if ref.key not in refs:
            refs[ref.key] = entity.EntityProxy(ref)
        return refs[ref.key]

    if not json or len(json) == 0:
        raise SerializationException("no json for {0}".format({"key": key, "gid": gid}))

    cache.update(**{se.key: [se] for se in json})

    deserialized = deserialize(json[0].serialized, reference)
    registrar.register(deserialized, original=json[0].serialized)
    loaded = deserialized

    deeper = True
    new_depth = depth
    if reach:
        choice = reach(loaded, depth)
        if choice < 0:
            log.debug("reach! reach! reach!")
            deeper = False
        else:
            new_depth += choice

    if deeper:
        for referenced_key, proxy in refs.items():
            linked = await materialize(
                registrar=registrar,
                store=store,
                key=referenced_key,
                reach=reach,
                depth=new_depth,
                cache=cache,
            )
            proxy.__wrapped__ = linked  # type: ignore

    loaded.validate()

    if single_entity:
        return loaded

    return [v for v in [registrar.find_by_key(se.key) for se in json] if v]


def maybe_destroyed(e: entity.Entity) -> Optional[entity.Entity]:
    if e.props.destroyed:
        log.info("destroyed: %s", e)
        return None
    return e


def registrar(
    registrar: entity.Registrar, modified: bool = False, **kwargs
) -> Dict[storage.Keys, Optional[str]]:
    return {
        storage.Keys(key=entity.key, gid=entity.props.gid): serialize(
            maybe_destroyed(entity), secure=True, **kwargs
        )
        for key, entity in registrar.entities.items()
        if not modified or entity.modified
    }


def modified(r: entity.Registrar, **kwargs) -> Dict[storage.Keys, Optional[str]]:
    return {
        key: serialized
        for key, serialized in registrar(r, modified=False, **kwargs).items()
        if key.key
        and r.was_modified_from_original(key.key, r.find_by_key(key.key), serialized)
    }


def for_update(entities: List[entity.Entity], **kwargs) -> Dict[storage.Keys, str]:
    return {
        storage.Keys(key=entity.key, gid=entity.props.gid): serialize(
            entity, secure=True, **kwargs
        )
        for entity in entities
    }
