from typing import Type, List, Union, Any, Dict

import abc
import copy
import logging
import props
import behavior
import crypto

log = logging.getLogger("dimsum")

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


class Finder:
    def find_things(self, criteria: Criteria) -> List["Entity"]:
        return []


class Entity(Finder):
    def __init__(
        self,
        key: str = None,
        identity: crypto.Identity = None,
        details: props.Details = None,
        behaviors: behavior.BehaviorMap = None,
        creator: "Entity" = None,
        kind: Kind = None,
        related: Dict[str, Kind] = None,
        frozen: Any = None,
        destroyed=None,
        **kwargs
    ):
        super().__init__(**kwargs)  # type: ignore
        self.kind = kind if kind else Kind()
        # Ignoring this error because we only ever have a None creator if we're the world.
        self.creator: "Entity" = creator if creator else None  # type: ignore
        self.frozen: Any = frozen if frozen else {}
        self.destroyed: bool = destroyed if destroyed else False

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

        self.details = details if details else props.Details("Unknown")
        self.behaviors = behaviors if behaviors else behavior.BehaviorMap()
        self.related: Dict[str, Kind] = related if related else {}

    def clone(self, **kwargs) -> "Entity":
        state_copy = copy.deepcopy(self.__dict__)
        state_copy.update(**kwargs)
        klass = self.__class__
        log.info("klass: %s", klass)
        return klass(**state_copy)

    def get_kind(self, name: str) -> Kind:
        if not name in self.related:
            self.related[name] = Kind()
        return self.related[name]

    def touch(self) -> None:
        self.details.touch()

    def destroy(self) -> None:
        self.destroyed = True

    def validate(self) -> None:
        assert self.creator
        assert self.details

    def get_behaviors(self, name):
        return self.behaviors.get_all(name)

    def add_behavior(self, name, **kwargs):
        return self.behaviors.add(name, **kwargs)

    def describes(self, q: str) -> bool:
        return False

    def accept(self, visitor: "EntityVisitor") -> Any:
        raise Exception("unimplemented")


class Registrar:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entities: Dict[str, entity.Entity] = {}
        self.garbage: Dict[str, entity.Entity] = {}

    def register(self, entity: Union[Entity, Any]):
        self.entities[entity.key] = entity

    def unregister(self, entity: Union[Entity, Any]):
        entity.destroy()
        del self.entities[entity.key]
        self.garbage[entity.key] = entity

    def empty(self):
        return len(self.entities.keys()) == 0

    def all_of_type(self, klass: Type) -> List[Entity]:
        return [e for e in self.entities.values() if isinstance(e, klass)]
