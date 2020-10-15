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
            "behaviors": self.behaviors.map,
        }

    def load(self, world, properties):
        self.key = properties["key"]
        if "details" in properties:
            self.details = props.Details.from_map(properties["details"])
        if "behavior" in properties:
            self.behaviors = behavior.BehaviorMap(**properties["behavior"])

    def accept(self, visitor: EntityVisitor):
        raise Exception("unimplemented")
