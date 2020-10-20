import jsonpickle
import logging

import crypto
import entity
import game
import envo
import things
import living
import animals
import world

log = logging.getLogger("dimsum")


@jsonpickle.handlers.register(crypto.Identity, base=True)
class IdentityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return crypto.Identity(
            public=obj["public"], private=obj["private"], signature=obj["signature"]
        )

    def flatten(self, obj, data):
        data["public"] = obj.public
        data["signature"] = obj.signature
        if self.context.secure:
            data["private"] = obj.private
        return data


@jsonpickle.handlers.register(world.World, base=True)
class WorldHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return self.context.lookup(None)

    def flatten(self, obj, data):
        data["key"] = "world"
        return data


@jsonpickle.handlers.register(envo.Area)
@jsonpickle.handlers.register(things.Item)
@jsonpickle.handlers.register(things.Recipe)
@jsonpickle.handlers.register(animals.Player)
@jsonpickle.handlers.register(animals.Person)
@jsonpickle.handlers.register(animals.Animal)
class EntityHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return self.context.lookup(obj["key"])

    def flatten(self, obj, data):
        data["key"] = obj.key
        data["kind"] = obj.__class__.__name__
        data["name"] = obj.details.name
        return data


class SecureUnpickler(jsonpickle.pickler.Pickler):
    def __init__(self, secure=False, **kwargs):
        super().__init__()
        self.secure = secure


class CustomUnpickler(jsonpickle.unpickler.Unpickler):
    def __init__(self, lookup, **kwargs):
        super().__init__()
        self.lookup = lookup


def deriveFrom(klass):
    name = klass.__name__
    return type("Root" + name, (klass,), {})


allowed = [
    things.Item,
    things.Recipe,
    envo.Area,
    animals.Animal,
    animals.Person,
    animals.Player,
]
classes = {k: deriveFrom(k) for k in allowed}
inverted = {v: k for k, v in classes.items()}


def serialize_full(value):
    if isinstance(value, list):
        value = [serialize_full(item) for item in value]
    if isinstance(value, dict):
        value = {key: serialize_full(value) for key, value in value.items()}
    if value.__class__ in classes:
        klass = classes[value.__class__]
        return klass(**value.__dict__)
    return value


def serialize(value, indent=None, unpicklable=True, secure=False):
    prepared = serialize_full(value)
    return jsonpickle.encode(
        prepared,
        context=SecureUnpickler(secure=secure),
        indent=indent,
        unpicklable=unpicklable,
        make_refs=False,
    )


def deserialize(encoded, lookup):
    decoded = jsonpickle.decode(
        encoded, context=CustomUnpickler(lookup), classes=list(classes.values())
    )

    if type(decoded) in inverted:
        original = inverted[type(decoded)]
        return original(**decoded.__dict__)

    return decoded
