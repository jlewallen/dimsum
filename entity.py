import uuid
import props
import behavior
import crypto


class EntityVisitor:
    def item(self, item):
        pass

    def recipe(self, recipe):
        pass

    def person(self, person):
        pass

    def area(self, area):
        pass


class Entity:
    def __init__(
        self,
        key=None,
        identity=None,
        details=None,
        behaviors=None,
        owner=None,
        kind=None,
        frozen=None,
        visible=None,
        **kwargs
    ):
        self.kind = kind
        self.owner = owner
        self.visible = visible if visible else {}
        self.frozen = frozen if frozen else {}

        if identity:
            self.identity = identity
        else:
            # If we have an owner and no identity then we generate one
            # based on them, forming a chain.
            if self.owner:
                self.identity = crypto.generate_identity_from(self.owner.identity)
            else:
                self.identity = crypto.generate_identity()
            # If we aren't given a key, the default one is our public key.
            self.key = self.identity.public

        if key:
            self.key = key

        self.details = details if details else props.Details("Unknown")
        self.behaviors = behaviors

        if not self.behaviors:
            self.behaviors = behavior.BehaviorMap()

    def touch(self):
        self.details.touch()

    def validate(self):
        if not self.owner:
            raise Exception("entity owner required")
        if not self.details:
            raise Exception("entity owner required")

    def get_behaviors(self, name):
        return self.behaviors.get_all(name)

    def add_behavior(self, name, **kwargs):
        return self.behaviors.add(name, **kwargs)

    def describes(self, q: str):
        return False

    def accept(self, visitor: EntityVisitor):
        raise Exception("unimplemented")
