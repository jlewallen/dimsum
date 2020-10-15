import os
import logging
import quart
import quart_cors
import jwt
import base64
import hashlib

import game
import grammar
import evaluator


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

    def failure(self, reply):
        return {"kind": reply.__class__.__name__, "failure": reply.message}

    def success(self, reply):
        return {"kind": reply.__class__.__name__, "success": reply.message}

    def observed_person(self, observed):
        return observed.person.accept(self)

    def observed_item(self, observed):
        return observed.item.accept(self)

    def personal_observation(self, obs):
        return {
            "kind": obs.__class__.__name__,
            "personal": {
                "who": obs.who.accept(self),
            },
        }

    def detailed_observation(self, obs):
        return {
            "kind": obs.__class__.__name__,
            "detailed": {
                "who": obs.who.accept(self),
                "what": obs.what.accept(self),
            },
        }

    def area_observation(self, obs):
        return {
            "kind": obs.__class__.__name__,
            "area": {
                "who": obs.who.accept(self),
                "where": obs.where.accept(self),
                "people": [e.accept(self) for e in obs.people],
                "items": [e.accept(self) for e in obs.items],
            },
        }

    def behavior(self, b):
        return {"lua": b.lua}

    def behaviors(self, bs):
        return {key: self.behavior(value) for key, value in bs.items()}

    def recipe(self, recipe):
        return {
            "key": recipe.key,
            "url": self.entityUrl(recipe),
            "kind": recipe.__class__.__name__,
            "owner": self.ref(recipe.owner),
            "details": recipe.details.map,
            "behaviors": self.behaviors(recipe.behaviors),
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
                "details": item.details.map,
                "behaviors": self.behaviors(item.behaviors),
                "area": self.ref(item.area),
            }

        return {
            "key": item.key,
            "url": self.entityUrl(item),
            "kind": item.__class__.__name__,
            "owner": self.ref(item.owner),
            "details": item.details.map,
            "behaviors": self.behaviors(item.behaviors),
        }

    def area(self, area):
        return {
            "key": area.key,
            "url": self.entityUrl(area),
            "kind": area.__class__.__name__,
            "owner": self.ref(area.owner),
            "details": area.details.map,
            "behaviors": self.behaviors(area.behaviors),
            "entities": [self.ref(e) for e in area.entities()],
        }

    def person(self, person):
        return {
            "key": person.key,
            "url": self.entityUrl(person),
            "kind": person.__class__.__name__,
            "owner": self.ref(person.owner),
            "details": person.details.map,
            "behaviors": self.behaviors(person.behaviors),
            "holding": [self.ref(e) for e in person.holding],
            "memory": {key: self.ref(value) for key, value in person.memory.items()},
        }


def create(state):
    app = quart.Quart(__name__)
    app = quart_cors.cors(app)

    session_key_string = os.getenv("SESSION_KEY")
    session_key = base64.b64decode(session_key_string)

    def authenticate():
        # TODO HACK We just 500 in here for now.
        header = quart.request.headers["authorization"]
        bearer, encoded = header.split(" ")
        decoded = jwt.decode(base64.b64decode(encoded), session_key, algorithms="HS256")
        return state.world, decoded

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    async def index(path):
        if path == "":
            return await app.send_static_file("index.html")
        file_path = "static/" + path
        if os.path.isfile(file_path):
            return await app.send_static_file(path)
        return await app.send_static_file("index.html")

    @app.route("/api")
    def main_index():
        authenticate()
        return areas_index()

    @app.route("/api/areas")
    def areas_index():
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        makeWeb = WebModelVisitor()

        return {"areas": [a.accept(makeWeb) for a in world.areas()]}

    @app.route("/api/people")
    def people_index():
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        makeWeb = WebModelVisitor()

        return {"people": [a.accept(makeWeb) for a in world.people()]}

    @app.route("/api/entities/<string:key>")
    def get_entity(key: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        logging.info("key: %s" % (key,))

        if world.contains(key):
            entity = world.find(key)
            makeWeb = WebModelVisitor()
            return {"entity": entity.accept(makeWeb)}

        return {"entity": None}

    @app.route("/api/entities/<string:key>/details", methods=["POST"])
    async def update_entity_details(key: str):
        world, token = authenticate()
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
            entity.details.update(form)
            entity.owner = owner

            await state.save()

            makeWeb = WebModelVisitor()
            return {"entity": entity.accept(makeWeb)}

        return {"entity": None}

    @app.route("/api/entities/<string:key>/behavior", methods=["POST"])
    async def update_entity_behavior(key: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        logging.info("key: %s" % (key,))

        if world.contains(key):
            form = await quart.request.get_json()
            logging.info("form: %s" % (form,))

            entity = world.find(key)
            entity.behaviors.replace(form)
            await state.save()

            makeWeb = WebModelVisitor()
            return {"entity": entity.accept(makeWeb)}

        return {"entity": None}

    @app.route("/api/repl", methods=["POST"])
    async def repl():
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        form = await quart.request.get_json()
        command = form["command"]

        l = grammar.create_parser()

        def parse_as(evaluator, full):
            tree = l.parse(full.strip())
            logging.info(str(tree))
            return evaluator.transform(tree)

        person_key = token["key"]
        player = world.find(person_key)
        action = parse_as(evaluator.create(world, player), command)
        reply = await world.perform(player, action)
        await state.save()

        makeWeb = WebModelVisitor()
        return {"reply": reply.accept(makeWeb)}

    @app.route("/api/login", methods=["POST"])
    async def login():
        world = state.world
        if world is None:
            return {"loading": True}

        form = await quart.request.get_json()

        name = form["name"]
        password = form["password"]

        person = world.find_person_by_name(name)
        if not person:
            raise Exception("no way")

        if not "s:password" in person.details.map:
            raise Exception("no way")

        saltEncoded, keyEncoded = person.details.map["s:password"]
        salt = base64.b64decode(saltEncoded)
        key = base64.b64decode(keyEncoded)
        actual_key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100000
        )

        token = {
            "key": person.key,
        }

        encoded = base64.b64encode(
            jwt.encode({"key": person.key}, session_key, algorithm="HS256")
        )

        return {"token": encoded.decode("utf-8"), "person": None}

    return app
