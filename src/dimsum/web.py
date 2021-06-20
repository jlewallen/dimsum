import os
import logging
import quart
import quart_cors
import jwt
import uuid
import base64
import hashlib

import model.game as game
import model.scopes.users as users
import model.scopes.behavior as behavior
import model.scopes as scopes

import serializing
import grammars

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
            decoded = jwt.decode(encoded, session_key, algorithms="HS256")
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
        return serializing.serialize({})

    @app.route("/api/areas")
    def areas_index():
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        return serializing.serialize(
            {"areas": world.entities_of_klass(scopes.AreaClass)}, unpicklable=False
        )

    @app.route("/api/people")
    def people_index():
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        return serializing.serialize(
            {"people": world.entities_of_klass(scopes.LivingClass)}, unpicklable=False
        )

    @app.route("/api/entities/<string:ukey>")
    def get_entity(ukey: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        key = url_key(ukey)
        log.info("key: %s" % (key,))

        if world.contains(key):
            entity = world.find_by_key(key)
            return serializing.serialize({"entity": entity})

        return {"entity": None}

    @app.route("/api/entities/<string:ukey>/props", methods=["POST"])
    async def update_entity_props(ukey: str):
        world, token = authenticate()
        if world is None:
            return {"loading": True}

        key = url_key(ukey)
        log.info("key: %s" % (key,))

        if world.contains(key):
            form = await quart.request.get_json()
            log.info("form: %s" % (form,))

            del form["key"]

            entity = world.find_by_key(key)
            entity.props.update(form)
            entity.touch()
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

            entity = world.find_by_key(key)
            with entity.make(behavior.Behaviors) as behave:
                behave.behaviors.replace(form)
            entity.touch()
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

        l = grammars.create_parser()

        person_key = token["key"]
        player = world.find_by_key(person_key)

        tree, create_evaluator = l.parse(command.strip())
        tree_eval = create_evaluator(world, player)
        log.info(str(tree))
        action = tree_eval.transform(tree)

        reply = await world.perform(action, player)
        await state.save()

        return serializing.serialize({"id": uuid.uuid1(), "reply": reply})

    @app.route("/api/login", methods=["POST"])
    async def login():
        world = state.world
        if world is None:
            return {"loading": True}

        form = await quart.request.get_json()

        name = form["name"]
        password = form["password"]

        key = base64.b64encode(name).decode("utf-8")
        person = world.find_entity_by_key(key)
        if not person:
            raise Exception("no way")

        with person.make(users.Auth) as auth:
            token = auth.try_password(password)

            if token:
                jwt_token = jwt.encode(token, session_key, algorithm="HS256")
                return {
                    "token": jwt_token,
                    "person": None,
                }

    @app.route("/api/storage/entities/<string:ukey>")
    def get_storage_entity(ukey: str):
        return {}

    return app
