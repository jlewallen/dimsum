import dataclasses
import copy
import enum
import sys
import copy
import functools
import pprint
import wrapt
import traceback
import jsondiff
import json
from datetime import datetime
from collections import ChainMap
from typing import (
    Callable,
    Union,
    Dict,
    List,
    Optional,
    Iterable,
    Any,
    Type,
    TypeVar,
    Tuple,
)

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
PyRefKey = "py/ref"
PyObjectKey = "py/object"
PyTypeKey = "py/type"


# From stackoverflow
def full_class_name(klass):
    module = klass.__module__
    return module + "." + klass.__qualname__


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


class SerializationException(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class RestoreContext:
    classes: List[Type] = dataclasses.field(default_factory=list)
    lookup: Dict[str, Type] = dataclasses.field(default_factory=dict)
    add_reference: Optional[Callable] = None
    depth: int = 0

    @functools.cached_property
    def classes_map(self):
        return {self._importable_name(c): c for c in self.classes or []}

    def increase(self) -> "RestoreContext":
        return RestoreContext(
            classes=self.classes, lookup=self.lookup, depth=self.depth + 1
        )

    def load_class(self, module_and_name: str):
        """
        Loads the module and returns the class.
        >>> cls = loadclass('datetime.datetime')
        >>> cls.__name__
        'datetime'
        >>> loadclass('does.not.exist')
        >>> loadclass('builtins.int')()
        0

        This is copied from jsonpickle.
        """
        # Check if the class exists in a caller-provided scope
        if self.classes_map:
            try:
                return self.classes_map[module_and_name]
            except KeyError:
                pass
        # Otherwise, load classes from globally-accessible imports
        names = module_and_name.split(".")
        # First assume that everything up to the last dot is the module name,
        # then try other splits to handle classes that are defined within
        # classes
        for up_to in range(len(names) - 1, 0, -1):
            module = ".".join(names[:up_to])
            try:
                __import__(module)
                obj = sys.modules[module]
                for class_name in names[up_to:]:
                    obj = getattr(obj, class_name)
                return obj
            except (AttributeError, ImportError, ValueError):
                continue
        return None

    def _importable_name(self, cls):
        """
        >>> class Example(object):
        ...     pass
        >>> ex = Example()
        >>> importable_name(ex.__class__) == 'jsonpickle.util.Example'
        True
        >>> importable_name(type(25)) == 'builtins.int'
        True
        >>> importable_name(None.__class__) == 'builtins.NoneType'
        True
        >>> importable_name(False.__class__) == 'builtins.bool'
        True
        >>> importable_name(AttributeError) == 'builtins.AttributeError'
        True
        """
        # Use the fully-qualified name if available (Python >= 3.3)
        name = getattr(cls, "__qualname__", cls.__name__)
        return "{}.{}".format(cls.__module__, name)


@functools.singledispatch
def _restore_value(value, ctx: RestoreContext) -> Any:
    return value


@_restore_value.register
def _restore_value_list(value: list, ctx: RestoreContext) -> Any:
    return [_restore_value(v, ctx) for v in value]


def _restore_value_obj_version(value: dict, ctx: RestoreContext):
    return Version(i=value["i"])


def _restore_value_obj_entity_ref(value: dict, ctx: RestoreContext):
    try:
        pyObject = value[PyRefKey]
        del value[PyRefKey]
        ref = EntityRef.new(pyObject=pyObject, **value)
        assert ctx.add_reference
        return ctx.add_reference(ref)
    except:
        log.exception("error:entity-ref value=%s", value, exc_info=True)
        raise


def _restore_value_obj_datetime(value: dict, ctx: RestoreContext):
    return datetime.fromisoformat(value["time"])


_handlers = {
    "model.entity.Version": _restore_value_obj_version,
    "model.entity.EntityRef": _restore_value_obj_entity_ref,
    "datetime.datetime": _restore_value_obj_datetime,
}


@_restore_value.register
def _restore_value_dict(value: dict, ctx: RestoreContext) -> Any:
    def restore_all():
        try:
            return {key: _restore_value(v, ctx) for key, v in value.items()}
        except:
            log.error("error:restore-all value=%s", value)
            raise

    def restore_children():
        try:
            return {
                key: _restore_value(v, ctx)
                for key, v in value.items()
                if key not in [PyObjectKey]
            }
        except:
            log.error("error:restore-children value=%s", value)
            raise

    if PyObjectKey in value:
        try:
            class_name = value[PyObjectKey]
            if class_name in _handlers:
                try:
                    return _handlers[class_name](restore_children(), ctx)
                except:
                    log.error(
                        "error:handler class-name=%s handler=%s",
                        class_name,
                        _handlers[class_name],
                    )
                    raise
            ctor = ctx.load_class(class_name)
            if ctor:
                restored = restore_children()
                try:
                    return ctor(**restored)
                except:
                    log.error(
                        "error: class-name=%s ctor=%s restored=%s",
                        class_name,
                        ctor,
                        restored,
                        exc_info=True,
                    )
                    raise
        except:
            log.error("error:object value=%s", value)
            raise
    if PyTypeKey in value:
        return ctx.load_class(value[PyTypeKey])
    return restore_all()


@dataclasses.dataclass(frozen=True)
class FlattenContext:
    identities: Identities = Identities.PUBLIC
    depth: int = 1

    def decrease(self) -> "FlattenContext":
        assert self.depth > 0
        return FlattenContext(identities=self.identities, depth=self.depth - 1)

    def path(self, key: str) -> "FlattenContext":
        return self


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
        key: _flatten_value(v, ctx.path(key))
        for key, v in value.items()
        if _include_key(key)
    }


def _py_object(obj: Any, **kwargs) -> Dict[str, Any]:
    return {
        **{"py/object": full_class_name(obj.__class__)},
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
def _flatten_value_object(value: object, ctx: FlattenContext) -> Any:
    # I wish there was a way to get singledisapatch to respect this,
    # but there's simply no way that I can tell.
    if isinstance(value, type):
        return {"py/type": full_class_name(value)}
    return _py_object(value, **_flatten_value_dict(value.__dict__, ctx))


@_flatten_value.register
def _flatten_value_enum(value: enum.Enum, ctx: FlattenContext) -> Any:
    return _py_object(value, value=str(value))


@_flatten_value.register
def _flatten_value_datetime(value: datetime, ctx: FlattenContext) -> Any:
    return {
        "py/object": "datetime.datetime",
        "time": value.isoformat(),
    }


@_flatten_value.register
def _flatten_value_entity(value: Entity, ctx: FlattenContext) -> Any:
    if ctx.depth > 0:
        return _py_object(value, **_flatten_value_dict(value.__dict__, ctx.decrease()))
    else:
        assert isinstance(value, Entity)
        assert value.props.name
        ref = EntityRef(
            key=value.key,
            klass=value.klass.__name__,
            name=value.props.name,
            pyObject=full_class_name(value.__class__),
        )
        return _flatten_value(ref, ctx)


@_flatten_value.register
def _flatten_value_entity_ref(value: EntityRef, ctx: FlattenContext) -> Any:
    return {
        "py/object": full_class_name(EntityRef),
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


def _deserialize(compiled: CompiledJson, lookup):
    return _restore_value(
        compiled.compiled, RestoreContext(classes=[Entity, World], add_reference=lookup)
    )


def deserialize_non_entity(
    value: Union[str, Dict[str, Any]], classes: Optional[List[Type]] = None
):
    if isinstance(value, str):
        value = json.loads(value)
    return _restore_value(value, RestoreContext(classes=classes or []))


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
    migrate: Optional[Callable] = None,
) -> Materialized:
    assert registrar
    assert store

    def _noop_migration(v):
        return False, v

    migrate = migrate or _noop_migration
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
    migrated, after_migration = migrate(compiled)
    deserialized = _deserialize(after_migration, reference)
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
                migrate=migrate,
            )
            proxy.__wrapped__ = linked.one()

    loaded.validate()

    if migrated:
        loaded.touch()

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
