import copy
import dataclasses
import json
import logging
import time
import jsondiff
import shortuuid
import stringcase
from typing import Awaitable, Any, Callable, Dict, List, Optional, Type, Union

from .crypto import Identity, generate
from .kinds import Kind
from .properties import Common
from .permissions import Acls, Permission, EverybodyIdentity

log = logging.getLogger("dimsum.model.entity")

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


def default_permissions_for(entity: "Entity") -> "Acls":
    #
    owner_key = ""
    return (
        Acls()
        .add(Permission.READ, EverybodyIdentity)
        .add(Permission.EXECUTE, EverybodyIdentity)
        .add(Permission.WRITE, owner_key)
    )


def _get_ctor_key(ctor) -> str:
    return stringcase.camelcase(ctor.__name__)


def _get_instance_key(instance) -> str:
    return _get_ctor_key(instance.__class__)


@dataclasses.dataclass(frozen=True)
class Serialized:
    key: str
    serialized: str


@dataclasses.dataclass(frozen=True)
class EntityUpdate:
    serialized: str
    entity: Optional["Entity"] = None


@dataclasses.dataclass(frozen=True)
class Keys:
    key: str


@dataclasses.dataclass(frozen=True)
class EntityRef:
    key: str
    klass: str
    name: str
    pyObject: Any

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
            log.debug("ignored kwargs: {0}".format(kwargs))


class EntityFrozen(Exception):
    pass


class EntityClass:
    pass


class RootEntityClass(EntityClass):
    pass


class UnknownClass(EntityClass):
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
        chimeras=None,
        scopes=None,
        initialize=None,
        **kwargs
    ):
        super().__init__()
        self.version = version if version else Version(0)
        # It's important to just assign these and avoid testing for
        # None, as we may have a None target EntityProxy that needs to
        # be linked up later, and in that case we need to keep the
        # wrapt Proxy object.
        self.creator: Optional["Entity"] = creator
        self.parent: Optional["Entity"] = parent
        self.chimeras = chimeras if chimeras else {}
        self.klass: Type[EntityClass] = klass if klass else UnknownClass

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

        if scopes:
            for scope in scopes:
                args = {}
                if initialize and scope in initialize:
                    args = initialize[scope]

                log.debug("scope %s %s %s", scope, kwargs, args)
                with self.make(scope, **args) as change:
                    pass

        log.debug(
            "entity:ctor {0} {1} '{2}' creator={3} id={4} props={5}".format(
                self.key, self.version, self.props.name, creator, id(self), self.props
            )
        )

    def validate(self) -> None:
        assert self.key
        assert self.props
        # Ugly, keeping this around, though.
        if RootEntityClass == self.klass:
            pass
        else:
            assert self.creator

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

    def make_and_discard(self, ctor, **kwargs):
        return self.make(ctor, discarding=True, **kwargs)

    def has(self, ctor, **kwargs):
        key = _get_ctor_key(ctor)
        return key in self.chimeras

    def make(self, ctor, discarding=False, **kwargs):
        key = _get_ctor_key(ctor)

        chargs = {}
        if key in self.chimeras:
            chargs = self.chimeras[key]
        chargs.update(**kwargs)

        log.debug("%s splitting chimera: %s %s", self.key, key, chargs)
        child = ctor(chimera=self, discarding=discarding, **chargs)
        return child

    def update(self, child):
        key = child.chimera_key
        data = child.__dict__
        del data["chimera"]
        del data["discarding"]
        log.debug("%s updating chimera: %s %s", self.key, key, data)
        self.chimeras[key] = data

    def __repr__(self):
        return "{0} (#{1})".format(self.props.name, self.props.gid)

    def __hash__(self):
        return hash(self.key)


class Scope:
    def __init__(
        self, chimera: Optional[Entity] = None, discarding: bool = False, **kwargs
    ):
        super().__init__()
        assert chimera
        self.chimera = chimera
        self.discarding = discarding

    @property
    def chimera_key(self) -> str:
        return _get_instance_key(self)

    @property
    def ourselves(self):
        return self.chimera

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save()

    def discard(self):
        self.discarding = True

    def save(self):
        if self.discarding:
            return
        self.chimera.update(self)


class RegistrationException(Exception):
    pass


class Registrar:
    def __init__(self, **kwargs):
        super().__init__()
        log.info("registrar:ctor")
        self.entities: Dict[str, Entity] = {}
        self.garbage: Dict[str, Entity] = {}
        self.numbered: Dict[int, Entity] = {}
        self.key_to_number: Dict[str, int] = {}
        self.originals: Dict[str, str] = {}
        self.number: int = 0

    def purge(self):
        self.entities = {}
        self.garbage = {}
        self.numbered = {}
        self.key_to_number = {}
        self.originals = {}
        self.number = 0

    def number_of_entities(self):
        return len(self.entities)

    def get_diff_if_available(self, key: str, serialized: str):
        if key in self.originals:
            original = self.originals[key]
            # TODO Parsing/diffing entity JSON
            return jsondiff.diff(
                json.loads(original), json.loads(serialized), marshal=True
            )
        return None

    def was_modified_from_original(
        self, key: str, e: Optional[Entity], update: EntityUpdate
    ) -> bool:
        if key in self.originals:
            if self.originals[key] == update.serialized:
                return False
            original = self.originals[key]
            assert original
            if e and not e.modified and update.serialized:
                log.warning(
                    "%s: untouched save %s",
                    key,
                    jsondiff.diff(  # TODO Parsing/diffing entity JSON
                        json.loads(original),
                        json.loads(update.serialized),
                        marshal=True,
                    ),
                )
        return True

    def was_modified(self, e: Entity) -> bool:
        return e.modified

    def modified(self) -> Dict[str, Entity]:
        return {key: e for key, e in self.entities.items() if self.was_modified(e)}

    def register(
        self,
        entity: Union[Entity, List[Entity]],
        original: Optional[str] = None,
        depth: int = 0,
    ):
        if isinstance(entity, list):
            return [self.register(e) for e in entity]

        assigned = entity.registered(self.number)
        if original:
            self.originals[entity.key] = original
        if assigned in self.numbered:
            already = self.numbered[assigned]
            if already.key != entity.key:
                log.error("gid collision: %d", assigned)
                log.error("gid collision: registered key=%s '%s", already.key, already)
                log.error("gid collision: incoming key=%s '%s", entity.key, entity)
                raise RegistrationException(
                    "gid {0} already assigned to {1} (gave={2})".format(
                        assigned, already.key, self.number
                    )
                )

        overwrite = entity.key in self.entities
        if overwrite:
            log.info("[%d] register:overwrite %s '%s'", depth, entity.key, entity)
        else:
            log.info("[%d] register:new %s '%s'", depth, entity.key, entity)

        # We can instantiate entities in any order, so we need to
        # be sure this is always the greatest gid we've seen.
        if assigned + 1 > self.number:
            self.number = assigned + 1
        self.entities[entity.key] = entity
        self.numbered[assigned] = entity
        self.key_to_number[entity.key] = assigned

        return entity

    def contains(self, key) -> bool:
        return key in self.entities

    def entities_of_klass(self, klass: Type[EntityClass]):
        return [e for key, e in self.entities.items() if e.klass == klass]

    def find_by_gid(self, gid: int) -> Optional[Entity]:
        if gid in self.numbered:
            return self.numbered[gid]
        return None

    def find_by_key(self, key) -> Optional[Entity]:
        if key in self.entities:
            return self.entities[key]
        return None

    # TODO Move to tests.
    def find_entity_by_name(self, name):
        for key, e in self.entities.items():
            if name in e.props.name:
                return e
        return None

    def empty(self) -> bool:
        return len(self.entities.keys()) == 0

    def everything(self) -> List[Entity]:
        return list(self.entities.values())

    def all_of_type(self, klass: Type) -> List[Entity]:
        return [e for e in self.entities.values() if isinstance(e, klass)]

    def unregister(self, entity: Union[Entity, Any]):
        entity.destroy()
        self.garbage[entity.key] = entity

    @property
    def undestroyed(self) -> List[Entity]:
        return [e for e in self.entities.values() if e.props.destroyed is None]
