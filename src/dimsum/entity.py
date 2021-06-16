from typing import Optional, Type, List, Union, Any, Dict, Sequence, cast

import abc
import logging
import time
import copy
import wrapt
import properties
import behavior
import crypto

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

    def area(self, area):
        pass

    def animal(self, animal):
        pass


class Kind:
    def __init__(self, identity: crypto.Identity = None, **kwargs):
        self.identity: crypto.Identity = (
            identity if identity else crypto.generate_identity()
        )

    def same(self, other: "Kind") -> bool:
        if other is None:
            return False
        return self.identity.public == other.identity.public

    def __str__(self):
        return "kind<%s>" % (self.identity,)

    def __repr__(self):
        return str(self)


class Criteria:
    def __init__(self, name: str = None, **kwargs):
        super().__init__()
        self.name = name
        self.kwargs = kwargs


class Entity(behavior.BehaviorMixin):
    def __init__(
        self,
        key: str = None,
        kind: Kind = None,
        creator: "Entity" = None,
        parent: "Entity" = None,
        klass: str = None,
        identity: crypto.Identity = None,
        props: properties.Common = None,
        related: Dict[str, Kind] = None,
        frozen: Any = None,
        destroyed: bool = None,
        **kwargs
    ):
        super().__init__(**kwargs)  # type: ignore
        self.kind = kind if kind else Kind()
        # Ignoring this error because we only ever have a None creator if we're the world.
        self.creator: "Entity" = creator if creator else None  # type: ignore
        self.parent: "Entity" = parent if parent else None  # type: ignore
        self.klass = klass if klass else self.__class__.__name__

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

        # TODO Move to props
        self.frozen: Any = frozen if frozen else None
        self.destroyed: bool = destroyed if destroyed else False
        self.related: Dict[str, Kind] = related if related else {}

        assert props

        self.props: properties.Common = props

        initial_owner = self.creator if self.creator else self
        self.props.owner = self.props.owner if self.props.owner else initial_owner

        self.validate()

    def validate(self) -> None:
        assert self.key
        assert self.props
        # Ugly, keeping this around, though.
        if self.klass != "World":
            assert self.creator

    @abc.abstractmethod
    def gather_entities(self) -> List["Entity"]:
        raise NotImplementedError

    @abc.abstractmethod
    def find_item_under(self, **kwargs) -> Optional["Entity"]:
        raise NotImplementedError

    def get_kind(self, name: str) -> Kind:
        if not name in self.related:
            self.related[name] = Kind()
        return self.related[name]

    def touch(self) -> None:
        self.props[properties.Touched] = time.time()

    def destroy(self) -> None:
        self.destroyed = True

    def try_modify(self) -> None:
        if self.can_modify():
            return
        raise ItemFrozen()

    def can_modify(self) -> bool:
        return self.frozen is None

    def freeze(self, identity: crypto.Identity) -> bool:
        if self.frozen:
            raise Exception("already frozen")
        self.frozen = identity
        return True

    def unfreeze(self, identity: crypto.Identity) -> bool:
        if not self.frozen:
            raise Exception("already unfrozen")
        if self.frozen.public != identity.public:
            return False
        self.frozen = None
        return True

    def describes(self, q: str) -> bool:
        return False

    def accept(self, visitor: "EntityVisitor") -> Any:
        raise NotImplementedError


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
            log.info(
                "register:new {0} ({1}) #{2}".format(entity.key, entity, self.number)
            )
            self.entities[entity.key] = entity
            self.numbered[self.number] = entity
            self.key_to_number[entity.key] = self.number
            self.number += 1

    def find_by_number(self, number: int) -> Optional[Entity]:
        if number in self.numbered:
            return self.numbered[number]
        log.info("register:miss {0}".format(number))
        return None

    def unregister(self, entity: Union[Entity, Any]):
        entity.destroy()
        del self.entities[entity.key]
        self.garbage[entity.key] = entity

    def empty(self) -> bool:
        return len(self.entities.keys()) == 1

    def everything(self) -> List[Entity]:
        return list(self.entities.values())

    def all_of_type(self, klass: Type) -> List[Entity]:
        return [e for e in self.entities.values() if isinstance(e, klass)]


class ItemFrozen(Exception):
    pass


def entities(maybes: List[Any]) -> List[Entity]:
    return [cast(Entity, e) for e in maybes]
