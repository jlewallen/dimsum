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
    def __init__(self, **kwargs):
        if "owner" in kwargs:
            self.owner = kwargs["owner"]
        else:
            self.owner = None

        if "identity" in kwargs:
            self.identity = kwargs["identity"]
        else:
            # If we have an owner and no identity then we generate one
            # based on them, forming a chain.
            if self.owner:
                self.identity = crypto.generate_identity_from(self.owner.identity)
            else:
                self.identity = crypto.generate_identity()

            # If we aren't given a key, the default one is our public key.
            self.key = self.identity.public

        if "key" in kwargs:
            self.key = kwargs["key"]

        if "details" in kwargs:
            self.details = kwargs["details"]
        else:
            self.details = props.Details("Unknown")

        self.behaviors = behavior.BehaviorMap()

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

    def saved(self):
        return {
            "key": self.key,
            "details": self.details.map,
            # Unwraps the Behavior instances.
            "behaviors": {k: v.__dict__ for k, v in self.behaviors.map.items()},
            "identity": self.identity.saved(),
        }

    def load(self, world, properties):
        self.key = properties["key"]
        self.identity = crypto.Identity(**properties["identity"])
        if "details" in properties:
            self.details = props.Details.from_map(properties["details"])
        if "behaviors" in properties:
            self.behaviors = behavior.BehaviorMap(
                **{
                    key: behavior.Behavior(**value)
                    for key, value in properties["behaviors"].items()
                }
            )

    def accept(self, visitor: EntityVisitor):
        raise Exception("unimplemented")
