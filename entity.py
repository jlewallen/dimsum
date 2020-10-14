import uuid
import props


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

    def describes(self, q: str):
        return False

    def saved(self):
        return {
            "key": self.key,
            "details": self.details.map,
        }

    def load(self, world, properties):
        self.key = properties["key"]
        self.details = props.Details.from_map(properties["details"])

    def accept(self, visitor: EntityVisitor):
        raise Exception("unimplemented")
