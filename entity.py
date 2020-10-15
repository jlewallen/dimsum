import uuid
import props
import behavior


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
        if "key" in kwargs:
            self.key = kwargs["key"]
        else:
            self.key = str(uuid.uuid1())
        self.owner = kwargs["owner"] if "owner" in kwargs else None
        self.details = (
            kwargs["details"] if "details" in kwargs else props.Details("Unknown")
        )
        self.behaviors = behavior.BehaviorMap()

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
        }

    def load(self, world, properties):
        self.key = properties["key"]
        if "details" in properties:
            self.details = props.Details.from_map(properties["details"])
        if "behaviors" in properties:
            self.behaviors = behavior.BehaviorMap(
                **{
                    key: behavior.BehaviorMap(**value)
                    for key, value in properties["behaviors"].items()
                }
            )

    def accept(self, visitor: EntityVisitor):
        raise Exception("unimplemented")
