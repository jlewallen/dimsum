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
import serializing

log = logging.getLogger("dimsum.web")


def url_key(key):
    b = bytes.fromhex(key)
    return base64.b64encode(b).decode("utf-8")


def create(state):
    app = quart.Quart(__name__)
    app = quart_cors.cors(app)

    session_key_string = os.getenv("SESSION_KEY")
    session_key = base64.b64decode(session_key_string)

    def authenticate():
        if "authorization" in quart.request.headers:
            header = quart.request.headers["authorization"]
            bearer, encoded = header.split(" ")
            decoded = jwt.decode(
                base64.b64decode(encoded), session_key, algorithms="HS256"
            )
            return state.world, decoded
        raise Exception("unauthorized")

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

        return serializing.serialize({"areas": world.areas()})

    @app.route("/api/people")
    def people_index():
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        return serializing.serialize({"people": world.people()})

    @app.route("/api/entities/<string:ukey>")
    def get_entity(ukey: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        key = url_key(ukey)
        log.info("key: %s" % (key,))

        if world.contains(key):
            entity = world.find(key)
            return serializing.serialize({"entity": entity})

        return {"entity": None}

    @app.route("/api/entities/<string:ukey>/details", methods=["POST"])
    async def update_entity_details(ukey: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        key = url_key(ukey)
        log.info("key: %s" % (key,))

        if world.contains(key):
            form = await quart.request.get_json()
            log.info("form: %s" % (form,))

            del form["key"]

            entity = world.find(key)
            entity.details.update(form)

            await state.save()

            return serializing.serialize({"entity": entity})

        return {"entity": None}

    @app.route("/api/entities/<string:ukey>/behavior", methods=["POST"])
    async def update_entity_behavior(ukey: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        key = url_key(ukey)
        log.info("key: %s" % (key,))

        if world.contains(key):
            form = await quart.request.get_json()
            log.info("form: %s" % (form,))

            entity = world.find(key)
            entity.behaviors.replace(form)
            await state.save()

            return serializing.serialize({"entity": entity})

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
            log.info(str(tree))
            return evaluator.transform(tree)

        person_key = token["key"]
        player = world.find(person_key)
        action = parse_as(evaluator.create(world, player), command)
        reply = await world.perform(player, action)
        await state.save()

        return serializing.serialize({"reply": reply})

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
