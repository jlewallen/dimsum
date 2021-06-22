import logging
import ariadne
import os.path
import dataclasses
import base64
import jwt

import model.world as world
import model.domains as domains
import model.game as game
import model.scopes as scopes
import model.scopes.users as users

import serializing
import grammars
import storage
import config

log = logging.getLogger("dimsum")

entity = ariadne.ScalarType("Entity")


@entity.serializer
def serialize_entity(value):
    log.debug("ariadne:entity")
    return serializing.serialize(value, indent=True, reproducible=True)


reply = ariadne.ScalarType("Reply")


@reply.serializer
def serialize_reply(value):
    log.debug("ariadne:reply")
    return serializing.serialize(value, indent=True, reproducible=True)


@dataclasses.dataclass
class Credentials:
    username: str
    password: str


credentials = ariadne.ScalarType("Credentials")


@credentials.value_parser
def parse_credentials_value(value):
    log.info("ariadne:credentials: %s", value)
    return value


query = ariadne.QueryType()


@query.field("login")
async def login(obj, info, credentials):
    domain = info.context.domain
    creds = Credentials(**credentials)
    log.info("ariadne:login username=%s", creds.username)
    if not domain.registrar.contains(creds.username):
        raise ValueError("bad username or password")

    try:
        person = domain.registrar.find_by_key(creds.username)
        if person:
            with person.make(users.Auth) as auth:
                token = auth.try_password(creds.password)

                if token:
                    jwt_token = jwt.encode(
                        token, info.context.cfg.session_key, algorithm="HS256"
                    )
                    return jwt_token
    except:
        log.exception("login")

    raise ValueError("bad username or password")


@query.field("size")
async def resolve_size(_, info):
    domain = info.context.domain
    store = await domain.store.number_of_entities()
    registrar = domain.registrar.number_of_entities()
    log.info("ariadne:size store=%d registrar=%d", store, registrar)
    if registrar > store:
        return registrar
    return store


@query.field("world")
async def resolve_world(obj, info):
    domain = info.context.domain
    log.info("ariadne:world")
    return serialize_entity(domain.world)


@query.field("entities")
async def resolve_entities(obj, info, key):
    domain = info.context.domain
    log.info("ariadne:entities key=%s", key)
    entities = []
    if domain.registrar.contains(key):
        entities = [domain.registrar.find_by_key(key)]
    else:
        loaded = await domain.store.load_by_key(key)
        if loaded:
            entities = [loaded]

    log.info("ariadne:entities entities=%s", entities)
    return [serialize_entity(e) for e in entities]


@query.field("areas")
async def resolve_areas(obj, info):
    domain = info.context.domain
    log.info("ariadne:areas")
    entities = domain.registrar.entities_of_klass(scopes.AreaClass)
    log.info("ariadne:areas entities=%s", entities)
    return [serialize_entity(e) for e in entities]


@query.field("people")
async def resolve_people(obj, info):
    domain = info.context.domain
    log.info("ariadne:people")
    entities = domain.registrar.entities_of_klass(scopes.LivingClass)
    log.info("ariadne:people entities=%s", entities)
    return [serialize_entity(e) for e in entities]


class Evaluation:
    def __init__(self, reply, entities):
        super().__init__()
        self.reply = reply
        self.entities = entities


@query.field("language")
async def resolve_language(obj, info, criteria):
    domain = info.context.domain
    log.info("ariadne:language criteria=%s", criteria)

    l = grammars.create_parser()
    w = await domain.materialize(world.Key)
    assert w
    player = await domain.materialize(criteria["evaluator"])
    assert player
    tree, create_evaluator = l.parse(criteria["text"].strip())
    tree_eval = create_evaluator(w, player)
    action = tree_eval.transform(tree)
    reply = await domain.perform(action, player)

    log.info("reply: %s", reply)
    await domain.save()

    return Evaluation(
        serialize_reply(reply),
        [serialize_entity(e) for e in domain.registrar.entities.values()],
    )


evaluation = ariadne.ObjectType("Evaluation")


@evaluation.field("reply")
async def resolve_evaluation_reply(obj, info):
    log.info("evaluation:reply %s", obj)
    return None


@evaluation.field("entities")
async def resolve_evaluation_entities(obj, info):
    log.info("evaluation:entities %s", obj)
    return []


def create():
    for path in ["src/dimsum/schema.graphql", "schema.graphql"]:
        if os.path.exists(path):
            type_defs = ariadne.load_schema_from_path(path)
            return ariadne.make_executable_schema(type_defs, query)
    raise Exception("unable to find schema.graphql")


@dataclasses.dataclass
class AriadneContext:
    domain: domains.Domain
    cfg: config.Configuration


def context(request):
    log.info("ariadne:context %s", request)
    return AriadneContext(domain=domains.Domain(), cfg=config.Configuration())
