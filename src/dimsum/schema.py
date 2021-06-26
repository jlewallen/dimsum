from typing import List

import logging
import ariadne
import os.path
import dataclasses
import base64
import starlette.requests
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
keyed_entity = ariadne.ObjectType("KeyedEntity")


@dataclasses.dataclass
class KeyedEntity:
    key: str
    serialized: str


@dataclasses.dataclass
class EntityDiff:
    key: str
    serialized: str


@entity.serializer
def serialize_entity(value):
    log.debug("ariadne:entity")
    serialized = serializing.serialize(value, reproducible=True)
    return KeyedEntity(value.key, serialized)


reply = ariadne.ScalarType("Reply")


@reply.serializer
def serialize_reply(value):
    log.debug("ariadne:reply")
    return serializing.serialize(value, reproducible=True)


query = ariadne.QueryType()


@query.field("size")
async def resolve_size(_, info):
    domain = info.context.domain
    store = await domain.store.number_of_entities()
    with domain.session() as session:
        registrar = session.registrar.number_of_entities()
        log.info("ariadne:size store=%d registrar=%d", store, registrar)
        if registrar > store:
            return registrar
        return store


@query.field("world")
async def resolve_world(obj, info):
    domain = info.context.domain
    log.info("ariadne:world")
    with domain.session() as session:
        return serialize_entity(await session.prepare())


async def materialize(session, **kwargs):
    loaded = await session.materialize(**kwargs)
    if loaded:
        entities = [loaded]
        for other_key, other in session.registrar.entities.items():
            if other_key != loaded.key:
                entities.append(other)

    return [serialize_entity(e) for e in entities]


@query.field("entitiesByKey")
async def resolve_entities_by_key(obj, info, key):
    domain = info.context.domain
    log.info("ariadne:entities-by-key key=%s", key)
    with domain.session() as session:
        return await materialize(session, key=key)


@query.field("entitiesByGid")
async def resolve_entities_by_gid(obj, info, gid):
    domain = info.context.domain
    log.info("ariadne:entities-by-gid gid=%s", gid)
    with domain.session() as session:
        return await materialize(session, gid=gid)


@query.field("areas")
async def resolve_areas(obj, info):
    domain = info.context.domain
    log.info("ariadne:areas")
    with domain.session() as session:
        await session.prepare()
        entities = session.registrar.entities_of_klass(scopes.AreaClass)
        log.info("ariadne:areas entities=%s", entities)
        return [serialize_entity(e) for e in entities]


@query.field("people")
async def resolve_people(obj, info):
    domain = info.context.domain
    log.info("ariadne:people")
    with domain.session() as session:
        await session.prepare()
        entities = session.registrar.entities_of_klass(scopes.LivingClass)
        log.info("ariadne:people entities=%s", entities)
        return [serialize_entity(e) for e in entities]


class Evaluation:
    def __init__(self, reply, entities: List[KeyedEntity]):
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
            [serialize_entity(e) for e in session.registrar.entities.values()],
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


@dataclasses.dataclass
class Credentials:
    username: str
    password: str


@mutation.field("login")
async def login(obj, info, credentials):
    domain = info.context.domain
    creds = Credentials(**credentials)
    log.info("ariadne:login username=%s", creds.username)
    with domain.session() as session:
        await session.prepare()

        try:
            person = await session.materialize(key=creds.username)
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


@mutation.field("makeSample")
async def makeSample(obj, info):
    domain = info.context.domain
    log.info("ariadne:make-sample")

    with domain.session() as session:
        world = await session.prepare()

        number_before = session.registrar.number_of_entities()

        generics, area = library.create_example_world(session.world)
        session.register(generics.all)

        await session.add_area(area)
        await session.save()

        affected = session.registrar.number_of_entities() - number_before

    return {"affected": affected}


@mutation.field("update")
async def update(obj, info, entities):
    domain = info.context.domain
    log.info("ariadne:update entities=%d", len(entities))
    with domain.session() as session:
        await session.prepare()
        diffs = [KeyedEntity(row["key"], row["serialized"]) for row in entities]
        await session.materialize(json=diffs)
        await session.save()
        return {"affected": len(diffs)}


def create():
    for path in ["src/dimsum/dimsum.graphql", "dimsum.graphql"]:
        if os.path.exists(path):
            type_defs = ariadne.load_schema_from_path(path)
            return ariadne.make_executable_schema(type_defs, [query, mutation])
    raise Exception("unable to find dimsum.graphql")


@dataclasses.dataclass
class AriadneContext:
    domain: domains.Domain
    cfg: config.Configuration
    request: starlette.requests.Request


def context(cfg):
    domain = cfg.make_domain()

    def wrap(request):
        log.info("ariadne:context %s", request)
        return AriadneContext(domain=domain, cfg=cfg, request=request)

    return wrap
