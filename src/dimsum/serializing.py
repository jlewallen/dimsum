from typing import Dict, Any, List, Optional, Union

import copy
import jsonpickle
import logging
import enum
import wrapt

import model.crypto as crypto
import model.entity as entity
import model.world as world

import model.scopes.movement as movement

import storage

log = logging.getLogger("dimsum")

entity_types = {"model.entity.Entity": entity.Entity, "model.world.World": world.World}


# From stackoverflow
def _fullname(klass):
    module = klass.__module__
    if module == "builtins":
        return klass.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + klass.__qualname__


def _derive_from(klass):
    name = klass.__name__
    return type("Root" + name, (klass,), {})


classes = {k: _derive_from(k) for k in entity_types.values()}
inverted = {v: k for k, v in classes.items()}


class Identities(enum.Enum):
    PRIVATE = 1
    PUBLIC = 2
    HIDDEN = 3


@jsonpickle.handlers.register(entity.Version, base=True)
class VersionHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return entity.Version(i=obj["i"])

    def flatten(self, obj, data):
        data["i"] = obj.i
        return data


@jsonpickle.handlers.register(crypto.Identity, base=True)
class IdentityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return crypto.Identity(
            public=obj["public"], private=obj["private"], signature=obj["signature"]
        )

    def flatten(self, obj, data):
        if self.context.identities == Identities.HIDDEN:
            data["public"] = "<public>"
            data["signature"] = "<signature>"
            data["private"] = "<private>"
            return data

        data["public"] = obj.public
        data["signature"] = obj.signature
        if self.context.identities == Identities.PRIVATE:
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


@jsonpickle.handlers.register(entity.EntityRef)
class EntityRefHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        raise NotImplementedError

    def flatten(self, obj, data):
        assert obj.pyObject
        data["py/object"] = _fullname(obj.pyObject)
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
    def __init__(self, identities=Identities.PRIVATE, **kwargs):
        super().__init__(**kwargs)
        self.identities = identities


class CustomUnpickler(jsonpickle.unpickler.Unpickler):
    def __init__(self, lookup, **kwargs):
        super().__init__()
        self.lookup = lookup


class SerializationException(Exception):
    pass


def _prepare(value, depth=0):
    if isinstance(value, list):
        value = [_prepare(item, depth=depth + 1) for item in value]

    if isinstance(value, dict):
        value = {key: _prepare(value, depth=depth + 1) for key, value in value.items()}

    if value.__class__ in classes:
        log.debug(
            "swap class: %s -> %s (%s)", type(value), classes[value.__class__], value
        )
        attrs = copy.copy(value.__dict__)
        klass = classes[value.__class__]
        return klass(**attrs)
    return value


def serialize(
    value, indent=None, unpicklable=True, identities=Identities.PUBLIC, full=True
) -> Optional[str]:
    if value is None:
        return value

    prepared = _prepare(value) if full else value

    return jsonpickle.encode(
        prepared,
        indent=indent,
        unpicklable=unpicklable,
        make_refs=False,
        context=SecurePickler(
            unpicklable=unpicklable,
            identities=identities,
            make_refs=False,
        ),
    )


def _deserialize(encoded, lookup):
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
    depths: Dict[str, int] = {}

    def reference(ref: entity.EntityRef):
        if ref.key not in refs:
            refs[ref.key] = entity.EntityProxy(ref)
            depths[ref.key] = depth
        return refs[ref.key]

    if not json or len(json) == 0:
        raise SerializationException("no json for {0}".format({"key": key, "gid": gid}))

    cache.update(**{se.key: [se] for se in json})

    deserialized = _deserialize(json[0].serialized, reference)
    registrar.register(deserialized, original=json[0].serialized, depth=depth)
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
            log.debug("materialize: %s -> %s", loaded, referenced_key)
            linked = await materialize(
                registrar=registrar,
                store=store,
                key=referenced_key,
                reach=reach,
                depth=depths[referenced_key],
                cache=cache,
            )
            proxy.__wrapped__ = linked

    loaded.validate()

    if single_entity:
        return loaded

    return [v for v in [registrar.find_by_key(se.key) for se in json] if v]


def _entity_update(
    instance: entity.Entity, serialized: Optional[str]
) -> entity.EntityUpdate:
    assert serialized
    assert instance
    return entity.EntityUpdate(serialized, instance)


def for_update(
    entities: List[entity.Entity], everything: bool = True, **kwargs
) -> Dict[entity.Keys, entity.EntityUpdate]:
    return {
        entity.Keys(key=e.key): _entity_update(
            e, serialize(e, identities=Identities.PRIVATE, **kwargs)
        )
        for e in entities
        if everything or e.modified
    }


def modified(
    registrar: entity.Registrar, **kwargs
) -> Dict[entity.Keys, entity.EntityUpdate]:
    return {
        key: serialized
        for key, serialized in for_update(
            list(registrar.entities.values()), **kwargs
        ).items()
        if registrar.was_modified_from_original(
            key.key, registrar.find_by_key(key.key), serialized
        )
    }
