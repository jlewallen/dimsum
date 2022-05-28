import copy
import dataclasses
import json
import time
import jsondiff
import shortuuid
import functools
import stringcase
from typing import (
    Awaitable,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    TypeVar,
    cast,
)

from loggers import get_logger

from .crypto import Identity, generate
from .kinds import Kind
from .properties import Common
from .permissions import Acls


_key_fn: Callable = shortuuid.uuid


def set_entity_keys_provider(fn: Callable[[], str]) -> Callable[[], str]:
    global _key_fn
    previous = _key_fn
    _key_fn = fn
    return previous


_identity_fn: Callable = generate


def set_entity_identities_provider(
    fn: Callable[[], Identity]
) -> Callable[[], Identity]:
    global _identity_fn
    previous = _identity_fn
    _identity_fn = fn
    return previous


def generate_entity_identity(creator=None) -> Identity:
    return _identity_fn(creator=creator)


def _default_describe(entity: "Entity") -> str:
    return "{0} (#{1})".format(entity.props.name, entity.props.gid)


_describe_fn: Callable[["Entity"], str] = _default_describe


def set_entity_describe_handler(
    fn: Callable[["Entity"], str]
) -> Callable[["Entity"], str]:
    global _describe_fn
    previous = _describe_fn
    _describe_fn = fn
    return previous


def _default_cleanup(entity: "Entity", **kwargs):
    pass


_cleanup_fn: Callable = _default_cleanup


def set_entity_cleanup_handler(fn: Callable) -> Callable:
    global _cleanup_fn
    previous = _cleanup_fn
    _cleanup_fn = fn
    return previous


def cleanup_entity(entity: "Entity", **kwargs):
    global _cleanup_fn
    _cleanup_fn(entity, **kwargs)


async def _default_area(entity: "Entity") -> "Entity":
    raise NotImplementedError


_area_fn: Callable[["Entity"], Awaitable[Optional["Entity"]]] = _default_area


def set_entity_area_provider(
    fn: Callable[["Entity"], Awaitable[Optional["Entity"]]]
) -> Callable[["Entity"], Awaitable[Optional["Entity"]]]:
    global _area_fn
    previous = _area_fn
    _area_fn = fn
    return previous


async def find_entity_area_maybe(entity: "Entity") -> Optional["Entity"]:
    global _area_fn
    return await _area_fn(entity)


async def find_entity_area(entity: "Entity") -> "Entity":
    global _area_fn
    area = await _area_fn(entity)
    assert area
    return area


def _get_ctor_key(ctor) -> str:
    return stringcase.camelcase(ctor.__name__)


def _get_instance_key(instance) -> str:
    return _get_ctor_key(instance.__class__)


@dataclasses.dataclass(frozen=True)
class CompiledJson:
    text: str = dataclasses.field(repr=False)
    compiled: Dict[str, Any]

    @staticmethod
    def compile(text: str) -> "CompiledJson":
        return CompiledJson(text, json.loads(text))


@dataclasses.dataclass(frozen=True)
class Serialized:
    key: str
    serialized: str


@dataclasses.dataclass(frozen=True)
class Chimera:
    key: str
    loaded: Optional[CompiledJson] = None
    entity: Optional["Entity"] = None
    saving: Optional[CompiledJson] = None
    saved: Optional[CompiledJson] = None
    diff: Optional[Dict[str, Any]] = None


@dataclasses.dataclass(frozen=True)
class EntityRef:
    key: str
    klass: str
    name: str
    pyObject: str

    @staticmethod
    def new(key=None, klass=None, name=None, pyObject=None, **kwargs):
        assert key
        assert klass
        assert name
        assert pyObject
        return EntityRef(key, klass, name, pyObject)


class IgnoreExtraConstructorArguments:
    """
    This can be applied in the inheritance hierarchy to swallow unused
    kwargs that may end up left over in some construction scenarios.
    """

    def __init__(self, **kwargs):
        super().__init__()
        if len(kwargs) > 0:
            get_logger("dimsum.model.warnings").info(
                "ignored kwargs: {0}".format(kwargs)
            )


class EntityFrozen(Exception):
    pass


class EntityClass:
    pass


class RootEntityClass(EntityClass):
    pass


class UnknownClass(EntityClass):
    pass


class MissingEntityException(Exception):
    pass


class Version:
    def __init__(self, i: int):
        super().__init__()
        self.i = i
        self.dirty = False

    def touch(self):
        if self.dirty:
            return
        self.dirty = True

    def increase(self):
        self.i += 1

    @property
    def modified(self):
        return self.dirty

    def __str__(self):
        return "Version<{0}>".format(self.i)


def scope(wrapped=None):
    log = get_logger("dimsum.model.scopes")

    if wrapped is None:
        return functools.partial(scope)

    return wrapped


@dataclasses.dataclass
class ScopeAttributes:
    parent: "Entity"
    discarding: bool
    depth: int = 0


@dataclasses.dataclass
class Scope:
    _scope_attrs: ScopeAttributes

    @property
    def _scope_key(self) -> str:
        return _get_instance_key(self)

    @property
    def parent(self):
        return self._scope_attrs.parent

    @property
    def ourselves(self):
        return self._scope_attrs.parent

    def __enter__(self):
        attrs = self._scope_attrs
        if attrs.discarding:
            return self
        if attrs.depth >= 0:
            attrs.depth += 1
        return self

    def __exit__(self, type, value, traceback):
        attrs = self._scope_attrs
        if attrs.discarding:
            return
        if attrs.depth > 0:
            attrs.depth -= 1
            if attrs.depth == 0:
                self._save()

    def discard(self):
        attrs = self._scope_attrs
        attrs.discarding = True
        if attrs.depth > 0:
            attrs.parent.discard(self)

    def _save(self):
        attrs = self._scope_attrs
        if attrs.discarding:
            return
        attrs.parent.update(self)


MakeT = TypeVar("MakeT", bound=Scope)
MakeDiscardT = TypeVar("MakeDiscardT", bound=Scope)


class Entity:
    def __init__(
        self,
        key: Optional[str] = None,
        version: Optional[Version] = None,
        creator: Optional["Entity"] = None,
        parent: Optional["Entity"] = None,
        klass: Optional[Type[EntityClass]] = None,
        identity: Optional[Identity] = None,
        props: Optional[Common] = None,
        acls: Optional[Acls] = None,
        scopes=None,
        create_scopes=None,
        initialize=None,
        **kwargs,
    ):
        super().__init__()
        self.version = version if version else Version(0)
        # It's important to just assign these and avoid testing for
        # None, as we may have a None target EntityProxy that needs to
        # be linked up later, and in that case we need to keep the
        # wrapt Proxy object.
        self.creator: Optional["Entity"] = creator
        self.parent: Optional["Entity"] = parent
        self.scopes = scopes if scopes else {}
        self.klass: Type[EntityClass] = klass if klass else UnknownClass
        self._live: Dict[str, Scope] = {}

        if identity:
            self.identity = identity
        else:
            self.identity = generate_entity_identity(
                creator=self.creator.identity if self.creator else None
            )
            # If we aren't given a key, the default one is our public key.
            self.key = _key_fn()

        if key:
            self.key = key

        assert props

        self.props: Common = props

        def get_scope_classes():
            return (create_scopes if create_scopes else []) + (
                list(initialize.keys()) if initialize else []
            )

        for scope in get_scope_classes():
            args = {}
            if initialize and scope in initialize:
                args = initialize[scope]

            self._log().debug("scope %s %s %s", scope, kwargs, args)
            with self.make(scope, **args) as change:
                pass

        self.acls = acls if acls else Acls.owner_writes()

        self._log().debug(
            "entity:ctor {0} {1} '{2}' creator={3} id={4} props={5}".format(
                self.key, self.version, self.props.name, creator, id(self), self.props
            )
        )

    def __post_init__(self):
        self._live = {}

    def _log(self):
        return get_logger("dimsum.model.entity")

    def validate(self) -> None:
        assert self.key
        assert self.props
        # Ugly, keeping this around, though.
        if RootEntityClass == self.klass:
            pass
        else:
            assert self.creator

        for key, value in self.scopes.items():
            assert not isinstance(value, Scope)

    def registered(self, gid: int) -> int:
        """
        We return our own global id if we have one and the caller will
        ensure uniquness. Otherwise we accept the proposed gid.
        """
        if self.props.gid >= 0:
            return self.props.gid
        else:
            self.props.gid = gid
            return gid

    def get_kind(self, name: str) -> Kind:
        if not name in self.props.related:
            self.props.related[name] = Kind(
                identity=generate_entity_identity(creator=self.identity)
            )
            self.touch()
        return self.props.related[name]

    def touch(self) -> None:
        self.props.touch()
        self.version.touch()

    @property
    def modified(self) -> bool:
        return self.version.modified

    def try_modify(self) -> None:
        if self.can_modify():
            return
        raise EntityFrozen()

    def can_modify(self) -> bool:
        return self.props.frozen is None

    def destroy(self) -> None:
        self.props.destroyed = self.identity
        self.touch()

    def freeze(self, identity: Identity) -> bool:
        if self.props.frozen:
            raise EntityFrozen()
        self.props.frozen = identity
        self.touch()
        return True

    def unfreeze(self, identity: Identity) -> bool:
        if not self.props.frozen:
            raise Exception("unfrozen")
        if self.props.frozen.public != identity.public:
            return False
        self.props.frozen = None
        self.touch()
        return True

    def describe(self) -> str:
        return _describe_fn(self)

    def describes(self, q: Optional[str] = None, **kwargs) -> bool:
        if q:
            if q.lower() in self.props.name.lower():
                return True
            if q.lower() in self.props.described.lower():
                return True
        return False

    def make_and_discard(self, ctor: Type[MakeDiscardT], **kwargs) -> MakeDiscardT:
        return self.make(ctor, discarding=True, **kwargs)

    def has(self, ctor: Type, **kwargs) -> bool:
        key = _get_ctor_key(ctor)
        return key in self.scopes

    def make(self, ctor: Type[MakeT], discarding=False, **kwargs) -> MakeT:
        key = _get_ctor_key(ctor)

        if key in self._live:
            return cast(MakeT, self._live[key])

        chargs = {}
        if key in self.scopes:
            chargs = self.scopes[key]
        else:
            self._log().debug("add scope '%s' to %s", key, self)
        chargs.update(**kwargs)

        self._log().debug("%s splitting scopes: %s %s", self.key, key, chargs)
        try:
            child = ctor(
                _scope_attrs=ScopeAttributes(parent=self, discarding=discarding),
                **chargs,
            )
            if not discarding:
                self._live[key] = child
            return child
        except:
            self._log().exception(f"error creating scope {ctor}", exc_info=True)
            raise

    def drop_scope(self, ctor: Type) -> bool:
        if self.has(ctor):
            del self.scopes[_get_ctor_key(ctor)]
            return True
        return False

    def discard(self, child):
        pass

    def update(self, child):
        key = child._scope_key
        data = child.__dict__
        del data["_scope_attrs"]
        self.scopes[key] = data
        del self._live[key]
        self._log().debug("%s updating scopes: %s %s", self.key, key, data)

    def __repr__(self):
        if hasattr(self, "props"):
            return f"'{self.props.name} (#{self.props.gid})'"
        if hasattr(self, "key"):
            return f"PartialEntity<{self.key}>"
        return f"PartialEntity!"

    def __hash__(self):
        return hash(self.key)


class EntityConflictException(Exception):
    pass


class RegistrationException(Exception):
    pass


class Registrar:
    def __init__(self, **kwargs):
        super().__init__()
        self._log.debug("registrar:ctor")
        self._garbage: Dict[str, Entity] = {}
        self._entities: Dict[str, Entity] = {}
        self._originals: Dict[str, CompiledJson] = {}
        self._numbered: Dict[int, Entity] = {}
        self._key_to_number: Dict[str, int] = {}
        self._diffs: Dict[str, Dict[str, Any]] = {}
        self._number: int = 0

    @functools.cached_property
    def _log(self):
        return get_logger("dimsum.model.registrar")

    @property
    def entities(self) -> Dict[str, Entity]:
        return {key: e for key, e in self._entities.items()}

    @property
    def number(self) -> int:
        return self._number

    @number.setter
    def number(self, value: int):
        self._number = value

    def number_of_entities(self):
        return len(self._entities)

    # Called from the web.
    def get_diff_if_available(self, key: str):
        assert key in self._diffs[key]
        return self._diffs[key]

    def get_original_if_available(self, key: str) -> Optional[CompiledJson]:
        return self._originals[key] if key in self._originals else None

    def filter_modified(self, updating: Dict[str, CompiledJson]) -> Dict[str, Chimera]:
        return {
            key: Chimera(
                key,
                saving=compiled,
                diff=self._diffs[key] if key in self._diffs else None,
            )
            for key, compiled in updating.items()
            if self._was_modified_from_original(key, compiled)
        }

    def _was_modified_from_original(self, key: str, update: CompiledJson) -> bool:
        if key in self._originals:
            original = self._originals[key]
            assert original

            if original.text == update.text:
                return False

            # TODO Parsing/diffing entity JSON
            d = jsondiff.diff(
                original.compiled,
                update.compiled,
                marshal=True,
            )
            self._diffs[key] = d

            if key in self._entities:
                entity = self._entities[key]
                if entity and not entity.modified and update.text:
                    self._log.warning("%s: untouched save %s", key, d)
        return True

    def was_modified(self, e: Entity) -> bool:
        return e.modified

    def modified(self) -> Dict[str, Entity]:
        return {key: e for key, e in self._entities.items() if self.was_modified(e)}

    def register(
        self,
        entity: Union[Entity, List[Entity]],
        compiled: Optional[CompiledJson] = None,
        depth: int = 0,
    ):
        if isinstance(entity, list):
            return [self.register(e) for e in entity]

        assigned = entity.registered(self._number)
        if compiled:
            if entity.key not in self._originals:
                self._originals[entity.key] = compiled
        if assigned in self._numbered:
            already = self._numbered[assigned]
            if already.key != entity.key:
                self._log.error("gid collision: %d", assigned)
                self._log.error(
                    "gid collision: registered key=%s %s", already.key, already
                )
                self._log.error("gid collision: incoming key=%s %s", entity.key, entity)
                raise RegistrationException(
                    "gid {0} already assigned to {1} (gave={2})".format(
                        assigned, already.key, self._number
                    )
                )

        has_compiled = "" if compiled else "(no-original)"
        op = "overwrite" if entity.key in self._entities else "new"
        self._log.debug(
            "[%d] register:%s %s %s %s",
            depth,
            op,
            entity.key,
            entity,
            has_compiled,
        )

        # We can instantiate entities in any order, so we need to
        # be sure this is always the greatest gid we've seen.
        if assigned + 1 > self._number:
            self._number = assigned + 1
        self._entities[entity.key] = entity
        self._numbered[assigned] = entity
        self._key_to_number[entity.key] = assigned

        return entity

    def entities_of_klass(self, klass: Type[EntityClass]):
        return [e for key, e in self._entities.items() if e.klass == klass]

    def find_by_gid(self, gid: int) -> Optional[Entity]:
        if gid in self._numbered:
            return self._numbered[gid]
        return None

    def find_by_key(self, key) -> Optional[Entity]:
        if key in self._entities:
            return self._entities[key]
        return None

    # TODO Move to tests.
    def find_entity_by_name(self, name):
        for key, e in self._entities.items():
            if name in e.props.name:
                return e
        return None

    def unregister(self, entity: Union[Entity, Any]):
        entity.destroy()
        self._garbage[entity.key] = entity

    @property
    def undestroyed(self) -> List[Entity]:
        return [e for e in self._entities.values() if e.props.destroyed is None]

    def log_summary(self):
        self._log.info("registrar: %d entities", len(self._entities))
