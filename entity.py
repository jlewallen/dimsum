import props
import behavior
import crypto

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
    def __init__(self, identity=None, **kwargs):
        if identity:
            self.identity = identity
        else:
            self.identity = crypto.generate_identity()

    def same(self, other: "Kind"):
        if other is None:
            return False
        return self.identity.public == other.identity.public

    def __str__(self):
        return "kind<%s>" % (self.identity,)

    def __repr__(self):
        return str(self)


class Entity:
    def __init__(
        self,
        key=None,
        identity=None,
        details=None,
        behaviors=None,
        creator=None,
        kind=None,
        frozen=None,
        destroyed=None,
        visible=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.kind = kind if kind else Kind()
        self.creator = creator if creator else None
        self.visible = visible if visible else {}
        self.frozen = frozen if frozen else {}
        self.destroyed = destroyed if destroyed else False

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

    def get_kind(self, name: str) -> Kind:
        key = "k:" + name
        if not key in self.details.map:
            self.details.map[key] = Kind()
        return self.details.map[key]

    def touch(self):
        self.details.touch()

    def destroy(self):
        self.destroyed = True

    def validate(self):
        if not self.creator:
            raise Exception("entity creator required")
        if not self.details:
            raise Exception("entity details required")

    def get_behaviors(self, name):
        return self.behaviors.get_all(name)

    def add_behavior(self, name, **kwargs):
        return self.behaviors.add(name, **kwargs)

    def describes(self, q: str):
        return False

    def accept(self, visitor: "EntityVisitor"):
        raise Exception("unimplemented")
