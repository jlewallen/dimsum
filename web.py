import quart

app = quart.Quart(__name__)


get_world = None


class WebModelVisitor:
    def item(self, item):
        return {
            "key": item.key,
            "details": item.details.__dict__,
        }

    def area(self, area):
        return {
            "key": area.key,
            "details": area.details.__dict__,
            "entities": [e.accept(self) for e in area.entities()],
        }

    def person(self, person):
        return {
            "key": person.key,
            "details": person.details.__dict__,
            "holding": [e.accept(self) for e in person.holding],
        }


def use_world_from(get_world_fn):
    global get_world
    get_world = get_world_fn


@app.route("/")
def main_index():
    world = get_world()
    if world is None:
        return {"loading": True}

    makeWeb = WebModelVisitor()

    return {"areas": [a.accept(makeWeb) for a in world.areas()]}
