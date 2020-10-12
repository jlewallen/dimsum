import quart
import quart_cors
import logging


class WebModelVisitor:
    def entityUrl(self, e):
        return ("/api/entities/%s" % (e.key,),)

    def item(self, item):
        if item.area:
            return {
                "key": item.key,
                "url": self.entityUrl(item),
                "kind": item.__class__.__name__,
                "details": item.details.__dict__,
                "area": {
                    "key": item.area.key,
                    "url": self.entityUrl(item.area),
                    "kind": item.area.__class__.__name__,
                },
            }
        return {
            "key": item.key,
            "url": self.entityUrl(item),
            "kind": item.__class__.__name__,
            "details": item.details.__dict__,
        }

    def area(self, area):
        return {
            "key": area.key,
            "url": self.entityUrl(area),
            "kind": area.__class__.__name__,
            "details": area.details.__dict__,
            "entities": [e.accept(self) for e in area.entities()],
        }

    def person(self, person):
        return {
            "key": person.key,
            "url": self.entityUrl(person),
            "kind": person.__class__.__name__,
            "details": person.details.__dict__,
            "holding": [e.accept(self) for e in person.holding],
        }


app = quart.Quart(__name__)
app = quart_cors.cors(app)
get_world = None


def use_world_from(get_world_fn):
    global get_world
    get_world = get_world_fn


@app.route("/api")
def main_index():
    return areas_index()


@app.route("/api/areas")
def areas_index():
    world = get_world()
    if world is None:
        return {"loading": True}

    makeWeb = WebModelVisitor()

    return {"areas": [a.accept(makeWeb) for a in world.areas()]}


@app.route("/api/entities/<string:key>")
def get_entity(key: str):
    world = get_world()
    if world is None:
        return {"loading": True}

    logging.info("key: %s" % (key,))

    if world.contains(key):
        entity = world.find(key)
        makeWeb = WebModelVisitor()
        return {"entity": entity.accept(makeWeb)}

    return {"entity": None}


@app.route("/api/entities/<string:key>", methods=["POST"])
async def update_entity(key: str):
    world = get_world()
    if world is None:
        return {"loading": True}

    logging.info("key: %s" % (key,))

    if world.contains(key):
        form = await quart.request.get_json()
        logging.info("form: %s" % (form,))

        entity = world.find(key)
        entity.details.name = form["name"]
        entity.details.desc = form["desc"]
        # TODO Save

        makeWeb = WebModelVisitor()
        return {"entity": entity.accept(makeWeb)}

    return {"entity": None}
