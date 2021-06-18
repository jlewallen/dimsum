from typing import Optional, Type, List, Union, Any, Dict, Sequence, cast

import abc
import logging
import time
import copy
import wrapt
import properties
import crypto
import kinds

log = logging.getLogger("dimsum")


class EntityRef(wrapt.ObjectProxy):
    def __init__(self, targetOrKey: Union["Entity", str]):
        # If we've been given a key, then we're deserializing and use
        # a dummy target for the wrapped instance. Then, when we're
        # all done we fix these up.
        if isinstance(targetOrKey, str):
            super().__init__(object())
        else:
            super().__init__(targetOrKey)


# TODO Move this
class EntityVisitor:
    def item(self, item):
        pass

    def recipe(self, recipe):
        pass

    def person(self, person):
        pass

    def exit(self, exit):
        pass

    def area(self, area):
        pass

    def animal(self, animal):
        pass


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


class Entity:
    def __init__(
        self,
        key: str = None,
        kind: kinds.Kind = None,
        creator: "Entity" = None,
        parent: "Entity" = None,
        klass: str = None,
        chimeras=None,
        identity: crypto.Identity = None,
        props: properties.Common = None,
        scopes=None,
        **kwargs
    ):
        super().__init__(**kwargs)  # type: ignore
        # Ignoring this error because we only ever have a None creator if we're the world.
        self.creator: "Entity" = creator if creator else None  # type: ignore
        self.parent: "Entity" = parent if parent else None  # type: ignore
        self.klass = klass if klass else self.__class__.__name__
        self.chimeras = chimeras if chimeras else {}

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
                log.debug("scope %s %s", scope, kwargs)
                with self.make(
                    scope,
                ) as change:
                    change.constructed(
                        key=self.key,
                        identity=self.identity,
                        parent=self.parent,
                        creator=self.creator,
                        props=self.props,
                        **kwargs
                    )

        self.validate()

        # log.debug("entity:ctor: {0} '{1}'".format(self.key, self.props.name))

    def validate(self) -> None:
        assert self.key
        assert self.props
        # Ugly, keeping this around, though.
        if self.klass != "World":
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

    def describes(self, **kwargs) -> bool:
        return False

    def accept(self, visitor: "EntityVisitor") -> Any:
        raise NotImplementedError

    def __str__(self):
        return "{0} (#{1})".format(self.props.name, self.props.gid)

    def __repr__(self):
        return str(self)

    def make_and_discard(self, ctor, **kwargs):
        return self.make(ctor, **kwargs)

    def make(self, ctor, **kwargs):
        key = ctor.__name__

        chargs = kwargs
        if key in self.chimeras:
            chargs.update(**self.chimeras[key])

        log.debug("%s splitting chimera: %s", self.key, key)
        child = ctor(chimera=self, **chargs)
        return child

    def update(self, child):
        key = child.__class__.__name__
        data = child.__dict__
        del data["chimera"]
        log.debug("%s updating chimera: %s %s", self.key, key, data)
        self.chimeras[key] = data


class Spawned:
    def __init__(self, chimera: Entity = None, **kwargs):
        super().__init__()
        assert chimera
        self.chimera = chimera

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

    def register(self, entity: Union[Entity, Any]):
        if entity.key in self.entities:
            log.info(
                "register:noop {0} ({1}) #{2}".format(
                    entity.key, entity, self.key_to_number[entity.key]
                )
            )
        else:
            assigned = entity.registered(self.number)
            log.info(
                "register:new {0} ({1}) #{2} {3}".format(
                    entity.key, entity, assigned, self.number
                )
            )
            if assigned in self.numbered:
                assert self.numbered[assigned] == entity
            self.number = assigned + 1
            self.entities[entity.key] = entity
            self.numbered[assigned] = entity
            self.key_to_number[entity.key] = assigned

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
        del self.entities[entity.key]
        self.garbage[entity.key] = entity


def entities(maybes: List[Any]) -> List[Entity]:
    return [cast(Entity, e) for e in maybes]
