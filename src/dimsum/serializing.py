import dataclasses
import copy
import enum
import jsonpickle
import functools
import wrapt
import traceback
import jsondiff
import json
from datetime import datetime
from typing import Callable, Dict, List, Optional, Iterable, Any, Type, TypeVar

from storage import EntityStorage
from loggers import get_logger
from model import (
    Entity,
    EntityClass,
    World,
    Scope,
    Version,
    Registrar,
    Serialized,
    Identity,
    EntityRef,
    Permission,
    MissingEntityException,
    CompiledJson,
    Common,
)
import scopes.movement as movement

log = get_logger("dimsum")

entity_types = {"model.entity.Entity": Entity, "model.world.World": World}


# From stackoverflow
def _fullname(klass):
    module = klass.__module__
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


@jsonpickle.handlers.register(Identity, base=True)
class IdentityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return Identity(
            public=obj["public"], private=obj["private"], signature=obj["signature"]
        )


@jsonpickle.handlers.register(movement.Direction)
class DirectionHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        if "compass" in obj:
            name = obj["compass"].lower()
            for d in movement.Direction:
                if name == d.name.lower():
                    return d
        return None


@jsonpickle.handlers.register(EntityRef)
class EntityRefHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        pyObject = obj["py/ref"]
        ref = EntityRef.new(pyObject=pyObject, **obj)
        log.debug("entity-handler: %s", ref)
        return self.context.lookup(ref)


@jsonpickle.handlers.register(datetime, base=True)
class DateTimeHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return datetime.fromisoformat(obj["time"])


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


@dataclasses.dataclass(frozen=True)
class FlattenContext:
    identities: Identities = Identities.PUBLIC
    depth: int = 1

    def decrease(self) -> "FlattenContext":
        assert self.depth > 0
        return FlattenContext(identities=self.identities, depth=self.depth - 1)


class NoFlattenerException(Exception):
    pass


@functools.singledispatch
def _flatten_value(value, ctx: FlattenContext) -> Any:
    raise NoFlattenerException(f"no flattener: {value}")


def _include_key(key: str) -> bool:
    return not key.startswith("_")


@_flatten_value.register
def _flatten_value_dict(value: dict, ctx: FlattenContext) -> Any:
    return {
        key: _flatten_value(v, ctx) for key, v in value.items() if _include_key(key)
    }


def _py_object(obj: Any, **kwargs) -> Dict[str, Any]:
    return {
        **{"py/object": _fullname(obj.__class__)},
        **kwargs,
    }


@_flatten_value.register
def _flatten_value_string(value: str, ctx: FlattenContext) -> Any:
    return value


@_flatten_value.register
def _flatten_value_integer(value: int, ctx: FlattenContext) -> Any:
    return value


@_flatten_value.register
def _flatten_value_float(value: float, ctx: FlattenContext) -> Any:
    return value


@_flatten_value.register
def _flatten_value_list(value: list, ctx: FlattenContext) -> Any:
    return [_flatten_value(v, ctx) for v in value]


@_flatten_value.register
def _flatten_value_tuple(value: tuple, ctx: FlattenContext) -> Any:
    return [_flatten_value(v, ctx) for v in value]


@_flatten_value.register
def _flatten_value_none(value: None, ctx: FlattenContext) -> Any:
    return None


@_flatten_value.register
def _flatten_value_datetime(value: datetime, ctx: FlattenContext) -> Any:
    return {
        "py/object": "datetime.datetime",
        "time": value.isoformat(),
    }


@_flatten_value.register
def _flatten_value_object(value: object, ctx: FlattenContext) -> Any:
    # I wish there was a way to get singledisapatch to respect this,
    # but there's simply no way that I can tell.
    if isinstance(value, type):
        # log.warning("value(type): full-name=%s", _fullname(value))
        return {"py/type": _fullname(value)}
    return _py_object(value, **_flatten_value_dict(value.__dict__, ctx))


@_flatten_value.register
def _flatten_value_entity(value: Entity, ctx: FlattenContext) -> Any:
    if ctx.depth > 0:
        # log.warning("value(d): type=%s", type(value))
        return _py_object(value, **_flatten_value_dict(value.__dict__, ctx.decrease()))
    else:
        # log.warning("value(s): type=%s %s %s", type(value), value.klass, type(value.klass))
        ref = EntityRef(
            key=value.key,
            klass=value.klass.__name__,
            name=value.props.name,
            pyObject=_fullname(value.__class__),
        )
        return _flatten_value(ref, ctx)


@_flatten_value.register
def _flatten_value_entity_ref(value: EntityRef, ctx: FlattenContext) -> Any:
    return {
        "py/object": _fullname(EntityRef),
        "py/ref": value.pyObject,
        "key": value.key,
        "klass": value.klass,
        "name": value.name,
    }


@_flatten_value.register
def _flatten_value_version(value: Version, ctx: FlattenContext) -> Any:
    return _py_object(value, i=value.i)


@_flatten_value.register
def _flatten_value_identity(value: Identity, ctx: FlattenContext) -> Any:
    if ctx.identities == Identities.HIDDEN:
        return _py_object(
            value,
            **{
                "public": "<public>",
                "signature": "<signature>",
                "private": "<private>",
            },
        )

    if ctx.identities == Identities.PRIVATE:
        return _py_object(
            value,
            **{
                "public": value.public,
                "signature": value.signature,
                "private": value.private,
            },
        )

    return _py_object(
        value,
        **{
            "public": value.public,
            "signature": value.signature,
        },
    )


@_flatten_value.register
def _flatten_value_direction(value: movement.Direction, ctx: FlattenContext) -> Any:
    return _py_object(value, compass=value.name)


class ScopeNotSerializableException(Exception):
    pass


@_flatten_value.register
def _flatten_value_scope(value: Scope, ctx: FlattenContext) -> Any:
    raise ScopeNotSerializableException()


def _flatten(value, unpicklable=True, identities=Identities.PUBLIC):
    return _flatten_value(value, FlattenContext(identities=identities))


def serialize(
    value, indent=None, unpicklable=True, identities=Identities.PUBLIC
) -> Optional[str]:
    if value is None:
        return value

    try:
        flattened = _flatten(value, unpicklable=unpicklable, identities=identities)
        try:
            return json.dumps(flattened, indent=indent)
        except:
            log.error("flattened: %s", flattened)
            raise
    except ScopeNotSerializableException as e:
        log.error("open entity scope value=%s", value)
        log.error("open entity scope scopes=%s", value.scopes)
        raise e


restores: int = 0


def _deserialize(compiled: CompiledJson, lookup):
    global restores
    context = CustomUnpickler(lookup)
    # log.warning("%d restoring: %s", restores, compiled.compiled)
    restores += 1
    decoded = context.restore(
        compiled.compiled, reset=True, classes=list(classes.values()) + [Entity, World]
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
    store: Optional[EntityStorage] = None,
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

    loaded.__post_init__()

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
