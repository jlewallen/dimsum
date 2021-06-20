from typing import Optional, Type, List, Union, Any, Dict, Sequence, cast

import abc
import logging
import time
import copy
import wrapt
import inflect

import model.properties as properties
import model.crypto as crypto
import model.kinds as kinds

log = logging.getLogger("dimsum")
p = inflect.engine()


class EntityRef(wrapt.ObjectProxy):
    def __init__(self, targetOrKey: Union["Entity", str]):
        # If we've been given a key, then we're deserializing and use
        # a dummy target for the wrapped instance. Then, when we're
        # all done we fix these up.
        if isinstance(targetOrKey, str):
            super().__init__(None)
        else:
            super().__init__(targetOrKey)


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


global_hooks = Hooks()


def hooks(new_hooks: Hooks):
    global global_hooks
    global_hooks = new_hooks


def get_ctor_key(ctor) -> str:
    return ctor.__name__.lower()


def get_instance_key(instance) -> str:
    return get_ctor_key(instance.__class__)


class EntityClass:
    pass


class RootEntityClass(EntityClass):
    pass


class UnknownClass(EntityClass):
    pass


class Version:
    def __init__(self, i: int = 0):
        super().__init__()
        self.i = i
        self.o = i

    def inc(self):
        if self.i == self.o:
            self.i += 1


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
        self.version = version if version else Version()
        # It's important to just assign these and avoid testing for
        # None, as we may have a None target EntityRef that needs to
        # be linked up later, and in that case we need to keep the
        # wrapt Proxy object.
        self.creator: Optional["Entity"] = creator
        self.parent: Optional["Entity"] = parent
        self.chimeras = chimeras if chimeras else {}
        self.klass: Type[EntityClass] = klass if klass else UnknownClass

        if identity:
            self.identity = identity
        else:
            # If we have an creator and no identity then we generate one
            # based on them, forming a chain.
            if self.creator:
                self.identity = crypto.generate_identity_from(self.creator.identity)
            else:
                self.identity = crypto.generate_identity()
            # If we aren't given a key, the default one is our public key.
            self.key = self.identity.public

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
                    change.constructed(
                        key=self.key,
                        identity=self.identity,
                        parent=self.parent,
                        creator=self.creator,
                        props=self.props,
                        **kwargs
                    )

        log.debug(
            "entity:ctor {0} '{1}' creator={2} {3}".format(
                self.key, self.props.name, creator, creator.key if creator else "<none>"
            )
        )

    def validate(self) -> None:
        assert self.key
        assert self.props
        # Ugly, keeping this around, though.
        if RootEntityClass == self.klass:
            pass
        else:
            if self.creator is None:
                log.info("type %s", type(self.creator))
                log.info("no-creator: %s %s", self, self.key)
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
            self.props.related[name] = kinds.Kind()
        return self.props.related[name]

    def touch(self) -> None:
        self.props[properties.Touched] = time.time()

    def destroy(self) -> None:
        self.props.destroyed = self.identity

    def try_modify(self) -> None:
        if self.can_modify():
            self.version.inc()
            return
        raise EntityFrozen()

    def can_modify(self) -> bool:
        return self.props.frozen is None

    def freeze(self, identity: crypto.Identity) -> bool:
        if self.props.frozen:
            raise EntityFrozen()
        self.props.frozen = identity
        return True

    def unfreeze(self, identity: crypto.Identity) -> bool:
        if not self.props.frozen:
            raise Exception("unfrozen")
        if self.props.frozen.public != identity.public:
            return False
        self.props.frozen = None
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
        return self.make(ctor, **kwargs)

    def has(self, ctor, **kwargs):
        key = get_ctor_key(ctor)
        return key in self.chimeras

    def make(self, ctor, **kwargs):
        key = get_ctor_key(ctor)

        chargs = kwargs
        if key in self.chimeras:
            chargs.update(**self.chimeras[key])

        log.debug("%s splitting chimera: %s", self.key, key)
        child = ctor(chimera=self, **chargs)
        return child

    def update(self, child):
        key = child.chimera_key
        data = child.__dict__
        del data["chimera"]
        log.debug("%s updating chimera: %s %s", self.key, key, data)
        self.chimeras[key] = data

    def __repr__(self):
        return self.describe()


class Scope:
    def __init__(self, chimera: Entity = None, **kwargs):
        super().__init__()
        assert chimera
        self.chimera = chimera

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
        self.chimera.update(self)


class Registrar:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entities: Dict[str, entity.Entity] = {}
        self.garbage: Dict[str, entity.Entity] = {}
        self.numbered: Dict[int, entity.Entity] = {}
        self.key_to_number: Dict[str, int] = {}
        self.number: int = 0

    def number_of_entities(self):
        return len(self.entities)

    def purge(self):
        self.entities = {}
        self.garbage = {}
        self.numbered = {}
        self.key_to_number = {}
        self.number = 0

    def register(self, entity: Union[Entity, Any]):
        if entity.key in self.entities:
            log.info("register:noop {0} '{1}'".format(entity.key, entity))
        else:
            assigned = entity.registered(self.number)
            log.info("register:new {0} '{1}'".format(entity.key, entity))
            if assigned in self.numbered:
                assert self.numbered[assigned] == entity
            self.number = assigned + 1
            self.entities[entity.key] = entity
            self.numbered[assigned] = entity
            self.key_to_number[entity.key] = assigned

    def contains(self, key) -> bool:
        return key in self.entities

    def find_by_key(self, key) -> Entity:
        return self.entities[key]

    def entities_of_klass(self, klass: Type[EntityClass]):
        return [e for key, e in self.entities.items() if e.klass == klass]

    def add_entities(self, entities: List[Entity]):
        for entity in entities:
            log.debug("add-entity: %s %s", entity.key, entity)
            self.register(entity)

    def find_entity_by_name(self, name):
        for key, e in self.entities.items():
            if name in e.props.name:
                return e
        return None

    def find_by_number(self, number: int) -> Optional[Entity]:
        if number in self.numbered:
            return self.numbered[number]
        log.info("register:miss {0}".format(number))
        return None

    def empty(self) -> bool:
        return len(self.entities.keys()) == 1

    def everything(self) -> List[Entity]:
        return list(self.entities.values())

    def all_of_type(self, klass: Type) -> List[Entity]:
        return [e for e in self.entities.values() if isinstance(e, klass)]

    def unregister(self, entity: Union[Entity, Any]):
        entity.destroy()
        # del self.entities[entity.key]
        self.garbage[entity.key] = entity

    @property
    def undestroyed(self) -> List[Entity]:
        return [e for e in self.entities.values() if e.props.destroyed is None]
