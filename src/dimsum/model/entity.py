from typing import Optional, Type, List, Union, Any, Dict, Sequence, Callable, cast

import abc
import logging
import dataclasses
import stringcase
import time
import json
import copy
import wrapt
import inflect
import shortuuid
import jsondiff

import model.properties as properties
import model.crypto as crypto
import model.kinds as kinds

log = logging.getLogger("dimsum.model.entity")
p = inflect.engine()


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


class Hooks:
    def describe(self, entity: "Entity") -> str:
        return "{0} (#{1})".format(entity.props.name, entity.props.gid)


key_generator_fn = shortuuid.uuid


def keys(fn: Callable):
    global key_generator_fn
    previous = key_generator_fn
    key_generator_fn = fn
    return previous


identity_generator_fn = crypto.generate


def identities(fn: Callable):
    global identity_generator_fn
    previous = identity_generator_fn
    identity_generator_fn = fn
    return previous


def generate_identity(creator=None):
    return identity_generator_fn(creator=creator)


global_hooks = Hooks()


def hooks(new_hooks: Hooks):
    global global_hooks
    previous = global_hooks
    global_hooks = new_hooks
    return previous


def get_ctor_key(ctor) -> str:
    return stringcase.camelcase(ctor.__name__)


def get_instance_key(instance) -> str:
    return get_ctor_key(instance.__class__)


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
        key: str = None,
        version: Version = None,
        creator: "Entity" = None,
        parent: "Entity" = None,
        klass: Type[EntityClass] = None,
        identity: crypto.Identity = None,
        props: properties.Common = None,
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
            self.identity = generate_identity(
                creator=self.creator.identity if self.creator else None
            )
            # If we aren't given a key, the default one is our public key.
            self.key = key_generator_fn()

        if key:
            self.key = key

        assert props

        self.props: properties.Common = props

        if scopes:
            for scope in scopes:
                args = {}
                if initialize and scope in initialize:
                    args = initialize[scope]

                log.debug("scope %s %s %s", scope, kwargs, args)
                with self.make(scope, **args) as change:
                    if False:
                        change.constructed(
                            key=self.key,
                            identity=self.identity,
                            parent=self.parent,
                            creator=self.creator,
                            props=self.props,
                            **kwargs
                        )

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

    def get_kind(self, name: str) -> kinds.Kind:
        if not name in self.props.related:
            self.props.related[name] = kinds.Kind(
                identity=generate_identity(creator=self.identity)
            )
            self.touch()
        return self.props.related[name]

    def touch(self) -> None:
        self.props[properties.Touched] = time.time()
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

    def freeze(self, identity: crypto.Identity) -> bool:
        if self.props.frozen:
            raise EntityFrozen()
        self.props.frozen = identity
        self.touch()
        return True

    def unfreeze(self, identity: crypto.Identity) -> bool:
        if not self.props.frozen:
            raise Exception("unfrozen")
        if self.props.frozen.public != identity.public:
            return False
        self.props.frozen = None
        self.touch()
        return True

    def describe(self) -> str:
        return global_hooks.describe(self)

    def describes(self, q: str = None, **kwargs) -> bool:
        if q:
            if q.lower() in self.props.name.lower():
                return True
            if q.lower() in self.describe():
                return True
        return False

    def make_and_discard(self, ctor, **kwargs):
        return self.make(ctor, discard=True, **kwargs)

    def has(self, ctor, **kwargs):
        key = get_ctor_key(ctor)
        return key in self.chimeras

    def make(self, ctor, discard=False, **kwargs):
        key = get_ctor_key(ctor)

        chargs = {}
        if key in self.chimeras:
            chargs = self.chimeras[key]
        chargs.update(**kwargs)

        log.debug("%s splitting chimera: %s %s", self.key, key, chargs)
        child = ctor(chimera=self, discard=discard, **chargs)
        return child

    def update(self, child):
        key = child.chimera_key
        data = child.__dict__
        del data["chimera"]
        del data["discard"]
        log.debug("%s updating chimera: %s %s", self.key, key, data)
        self.chimeras[key] = data

    def __repr__(self):
        return self.describe()


class Scope:
    def __init__(self, chimera: Entity = None, discard: bool = False, **kwargs):
        super().__init__()
        assert chimera
        self.chimera = chimera
        self.discard = discard

    @property
    def chimera_key(self) -> str:
        return get_instance_key(self)

    @abc.abstractmethod
    def constructed(self, **kwargs):
        pass

    @property
    def ourselves(self):
        return self.chimera

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save()

    def save(self):
        if self.discard:
            return
        self.chimera.update(self)


class RegistrationException(Exception):
    pass


class Registrar:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        original: str = None,
        depth: int = 0,
    ):
        if isinstance(entity, list):
            return [self.register(e) for e in entity]

        if entity.key in self.entities:
            log.info("[%d] register:noop %s '%s'", depth, entity.key, entity)
        else:
            log.info("[%d] register:new %s '%s'", depth, entity.key, entity)
            assigned = entity.registered(self.number)
            if original:
                self.originals[entity.key] = original
            if assigned in self.numbered:
                already = self.numbered[assigned]
                if already.key != entity.key:
                    raise RegistrationException(
                        "gid {0} already assigned to {1} (gave={2})".format(
                            assigned, already.key, self.number
                        )
                    )
            # We can instantiate entities in any order, so we need to
            # be sure this is always the greatest gid we've seen.
            if assigned + 1 > self.number:
                self.number = assigned + 1
            self.entities[entity.key] = entity
            self.numbered[assigned] = entity
            self.key_to_number[entity.key] = assigned

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
