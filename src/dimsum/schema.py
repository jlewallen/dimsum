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
import model.library as library

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


@query.field("entitiesByKey")
async def resolve_entities_by_key(obj, info, key):
    domain = info.context.domain
    log.info("ariadne:entities-by-key key=%s", key)
    with domain.session() as session:
        entities = []
        loaded = await session.materialize(key=key)
        if loaded:
            entities = [loaded]

        log.info("ariadne:entities-by-key entities=%s", entities)
        return [serialize_entity(e) for e in entities]


@query.field("entitiesByGid")
async def resolve_entities_by_gid(obj, info, gid):
    domain = info.context.domain
    log.info("ariadne:entities-by-gid gid=%s", gid)
    with domain.session() as session:
        entities = []
        loaded = await session.materialize(gid=gid)
        if loaded:
            entities = [loaded]

        log.info("ariadne:entities-by-gid entities=%s", entities)
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
    with domain.session() as session:
        w = await session.materialize(key=world.Key)
        assert w
        player = await session.materialize(key=criteria["evaluator"])
        assert player
        tree, create_evaluator = l.parse(criteria["text"].strip())
        tree_eval = create_evaluator(w, player)
        action = tree_eval.transform(tree)
        reply = await session.perform(action, player)

        log.info("reply: %s", reply)
        await session.save()

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


mutation = ariadne.MutationType()


class UsernamePasswordError(ValueError):
    pass


@mutation.field("login")
async def login(obj, info, credentials):
    domain = info.context.domain
    creds = Credentials(**credentials)
    log.info("ariadne:login username=%s", creds.username)
    if not domain.registrar.contains(creds.username):
        raise UsernamePasswordError()

    try:
        person = domain.registrar.find_by_key(creds.username)
        if person:
            with person.make(users.Auth) as auth:
                token = auth.try_password(creds.password)

                if token:
                    log.info("successful login %s", token)
                    jwt_token = jwt.encode(
                        token, info.context.cfg.session_key, algorithm="HS256"
                    )
                    return jwt_token
    except:
        log.exception("login")

    raise UsernamePasswordError()


@mutation.field("purge")
async def purge(obj, info):
    domain = info.context.domain
    log.info("ariadne:purge")
    return {"affected": 0}


@mutation.field("makeSample")
async def makeSample(obj, info):
    domain = info.context.domain
    log.info("ariadne:make-sample")

    number_before = domain.registrar.number_of_entities()

    if domain.world is None:
        domain.world = world.World()

    generics, area = library.create_example_world(domain.world)
    with domain.session() as session:
        session.registrar.add_entities(generics.all)
        session.add_area(area)
        await session.save()

    affected = domain.registrar.number_of_entities() - number_before

    return {"affected": affected}


@mutation.field("update")
async def update(obj, info, entities):
    domain = info.context.domain
    log.info("ariadne:update entities=%d", len(entities))
    # TODO Parallel
    with domain.session() as session:
        instantiated = [await session.materialize(json=e) for e in entities]
        new_world = [e for e in instantiated if e.key == world.Key]
        if new_world:
            session.world = world
            domain.world = world  # TODO Remove
        await session.save()
        return {"affected": len(instantiated)}


def create():
    for path in ["src/dimsum/schema.graphql", "schema.graphql"]:
        if os.path.exists(path):
            type_defs = ariadne.load_schema_from_path(path)
            return ariadne.make_executable_schema(type_defs, [query, mutation])
    raise Exception("unable to find schema.graphql")


@dataclasses.dataclass
class AriadneContext:
    domain: domains.Domain
    cfg: config.Configuration


def context(cfg):
    domain = cfg.make_domain()

    def wrap(request):
        log.info("ariadne:context %s", request)
        return AriadneContext(domain=domain, cfg=cfg)

    return wrap
