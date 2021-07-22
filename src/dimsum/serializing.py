import dataclasses
import copy
import enum
import jsonpickle
import wrapt
from typing import Callable, Dict, List, Optional, Iterable

import storage
from loggers import get_logger
from model import (
    Entity,
    World,
    Version,
    Registrar,
    Serialized,
    Identity,
    EntityRef,
    Permission,
    MissingEntityException,
)
import scopes.movement as movement

from model.entity import CompiledJson

log = get_logger("dimsum")

entity_types = {"model.entity.Entity": Entity, "model.world.World": World}


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


class EntityProxy(wrapt.ObjectProxy):
    def __init__(self, ref: EntityRef):
        super().__init__(ref)
        self._self_ref = ref

    def __getattr__(self, *arg):
        if self.__wrapped__ is None:
            log.info("self.None __getattr__: %s %s", arg, self._self_ref)
        return super().__getattr__(*arg)

    def __deepcopy__(self, memo):
        return copy.deepcopy(self.__wrapped__, memo)

    def __repr__(self) -> str:
        assert self.__wrapped__
        return str(self.__wrapped__)

    def __str__(self) -> str:
        assert self.__wrapped__
        return str(self.__wrapped__)


@jsonpickle.handlers.register(Version, base=True)
class VersionHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return Version(i=obj["i"])

    def flatten(self, obj, data):
        data["i"] = obj.i
        return data


@jsonpickle.handlers.register(Identity, base=True)
class IdentityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return Identity(
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


@jsonpickle.handlers.register(EntityRef)
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


@jsonpickle.handlers.register(Entity)
@jsonpickle.handlers.register(World)
class EntityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        pyObject = entity_types[obj["py/object"]]
        ref = EntityRef.new(pyObject=pyObject, **obj)
        log.debug("entity-handler: %s", ref)
        return self.context.lookup(ref)

    def flatten(self, obj, data):
        data["key"] = obj.key
        data["klass"] = obj.klass.__name__
        data["name"] = obj.props.name
        return data


# @jsonpickle.handlers.register(Permission)
class JsonEnumHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        pass

    def flatten(self, obj: enum.Enum, data):
        return obj.name


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


def _deserialize(compiled: CompiledJson, lookup):
    context = CustomUnpickler(lookup)
    decoded = context.restore(
        compiled.compiled, reset=True, classes=list(classes.values())
    )
    if type(decoded) in inverted:
        original = inverted[type(decoded)]
        return original(**decoded.__dict__)
    return decoded


@dataclasses.dataclass()
class Materialized:
    entities: List[Entity]

    def empty(self) -> bool:
        return len(self.entities) == 0

    def maybe_one(self) -> Optional[Entity]:
        if len(self.entities) == 1:
            return self.entities[0]
        return None

    def one(self) -> Entity:
        if len(self.entities) == 1:
            return self.entities[0]
        raise MissingEntityException()

    def all(self) -> List[Entity]:
        return self.entities


async def materialize(
    registrar: Optional[Registrar] = None,
    store: Optional[storage.EntityStorage] = None,
    key: Optional[str] = None,
    gid: Optional[int] = None,
    json: Optional[List[Serialized]] = None,
    reach=None,
    depth: int = 0,
    cache: Optional[Dict[str, List[Serialized]]] = None,
    proxy_factory: Optional[Callable] = None,
    refresh: bool = False,
) -> Materialized:
    assert registrar
    assert store

    single_entity = json is None
    cache = cache or {}
    found = None
    if key is not None:
        if not refresh:
            log.debug("[%d] materialize key=%s", depth, key)
            found = registrar.find_by_key(key)
            if found:
                return Materialized([found])

        if key in cache:
            json = cache[key]
        else:
            json = await store.load_by_key(key)
            if len(json) == 0:
                log.info("[%d] %s missing key=%s", depth, store, key)
                return Materialized([])

    if gid is not None:
        if not refresh:
            log.debug("[%d] materialize gid=%d", depth, gid)
            found = registrar.find_by_gid(gid)
            if found:
                return Materialized([found])

        json = await store.load_by_gid(gid)
        if len(json) == 0:
            log.info("[%d] %s missing gid=%d", depth, store, gid)
            return Materialized([])

    log.debug("json: %s", json)

    refs: Dict[str, EntityProxy] = {}
    depths: Dict[str, int] = {}

    def reference(ref: EntityRef):
        if ref.key not in refs:
            refs[ref.key] = EntityProxy(ref)
            depths[ref.key] = depth
        return refs[ref.key]

    if not json or len(json) == 0:
        raise SerializationException("no json for {0}".format({"key": key, "gid": gid}))

    cache.update(**{se.key: [se] for se in json})

    serialized = json[0].serialized  # TODO why not all json?
    compiled = CompiledJson.compile(serialized)
    deserialized = _deserialize(compiled, reference)
    proxied = proxy_factory(deserialized) if proxy_factory else deserialized
    loaded = proxied

    deeper = True
    choice = 0
    if reach:
        choice = reach(loaded, depth)
        if choice < 0:
            log.debug("reach! reach! reach!")
            deeper = False
            choice = 0
        elif choice > 0:
            depths[loaded.key] = depths.setdefault(loaded.key, 0) + choice
            log.debug(
                "depth-change: %s choice=%d depth[loaded]=%d",
                loaded.klass,
                choice,
                depths[loaded.key],
            )

    registrar.register(loaded, compiled=compiled, depth=depth + choice)

    if deeper:
        for referenced_key, proxy in refs.items():
            log.debug("materialize: %s -> %s", loaded, referenced_key)
            linked = await materialize(
                registrar=registrar,
                store=store,
                key=referenced_key,
                reach=reach,
                depth=depths[referenced_key] + choice,
                proxy_factory=proxy_factory,
                cache=cache,
            )
            proxy.__wrapped__ = linked.one()

    loaded.validate()

    if single_entity:
        return Materialized([loaded])

    return Materialized(
        [v for v in [registrar.find_by_key(se.key) for se in json] if v]
    )


def for_update(
    entities: Iterable[Entity], everything: bool = True, **kwargs
) -> Dict[str, CompiledJson]:
    def _assert(s: Optional[str]) -> str:
        assert s
        return s

    return {
        e.key: CompiledJson.compile(
            _assert(serialize(e, identities=Identities.PRIVATE, **kwargs))
        )
        for e in entities
        if everything or e.modified
    }
