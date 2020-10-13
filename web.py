import quart
import quart_cors
import logging
import game


class WebModelVisitor:
    def entityUrl(self, e):
        return ("/api/entities/%s" % (e.key,),)

    def ref(self, entity):
        return {
            "key": entity.key,
            "url": self.entityUrl(entity),
            "kind": entity.__class__.__name__,
            "name": entity.details.name,
        }

    def recipe(self, recipe):
        return {
            "key": recipe.key,
            "url": self.entityUrl(recipe),
            "kind": recipe.__class__.__name__,
            "owner": self.ref(recipe.owner),
            "details": recipe.details.__dict__,
            "base": recipe.base,
            "required": {k: self.ref(e) for k, e in recipe.required.items()},
        }

    def item(self, item):
        if item.area:
            return {
                "key": item.key,
                "url": self.entityUrl(item),
                "kind": item.__class__.__name__,
                "owner": self.ref(item.owner),
                "details": item.details.__dict__,
                "area": self.ref(item.area),
            }

        return {
            "key": item.key,
            "url": self.entityUrl(item),
            "kind": item.__class__.__name__,
            "owner": self.ref(item.owner),
            "details": item.details.__dict__,
        }

    def area(self, area):
        return {
            "key": area.key,
            "url": self.entityUrl(area),
            "kind": area.__class__.__name__,
            "owner": self.ref(area.owner),
            "details": area.details.__dict__,
            "entities": [self.ref(e) for e in area.entities()],
        }

    def person(self, person):
        return {
            "key": person.key,
            "url": self.entityUrl(person),
            "kind": person.__class__.__name__,
            "owner": self.ref(person.owner),
            "details": person.details.__dict__,
            "holding": [self.ref(e) for e in person.holding],
            "memory": {key: self.ref(value) for key, value in person.memory.items()},
        }


def create(state):
    app = quart.Quart(__name__)
    app = quart_cors.cors(app)

    @app.route("/api")
    def main_index():
        return areas_index()

    @app.route("/api/areas")
    def areas_index():
        world = state.world
        if world is None:
            return {"loading": True}

        makeWeb = WebModelVisitor()

        return {"areas": [a.accept(makeWeb) for a in world.areas()]}

    @app.route("/api/people")
    def people_index():
        world = state.world
        if world is None:
            return {"loading": True}

        makeWeb = WebModelVisitor()

        return {"people": [a.accept(makeWeb) for a in world.people()]}

    @app.route("/api/entities/<string:key>")
    def get_entity(key: str):
        world = state.world
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
        world = state.world
        if world is None:
            return {"loading": True}

        logging.info("key: %s" % (key,))

        if world.contains(key):
            form = await quart.request.get_json()
            logging.info("form: %s" % (form,))

            # Verify we can find the owner.
            owner = world
            if world.contains(form["owner"]):
                owner = world.find(form["owner"])

            del form["key"]
            del form["owner"]

            entity = world.find(key)
            entity.details.__dict__.update(form)
            entity.owner = owner

            await state.save()

            makeWeb = WebModelVisitor()
            return {"entity": entity.accept(makeWeb)}

        return {"entity": None}

    return app
