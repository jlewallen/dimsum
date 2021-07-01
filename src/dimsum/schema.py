from typing import List, Optional, Any

import logging
import ariadne
import os.path
import json
import dataclasses
import base64
import jwt
import asyncio

import starlette.requests

import model.entity as entity
import model.world as world
import model.domains as domains
import model.game as game
import model.entity as entities
import model.scopes as scopes
import model.scopes.users as users
import model.library as library

import serializing
import grammars
import storage
import config

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class KeyedEntity:
    key: str
    serialized: str


@dataclasses.dataclass
class EntityDiff:
    key: str
    serialized: str


reply = ariadne.ScalarType("Reply")


@reply.serializer
def serialize_reply(value):
    log.debug("ariadne:reply")
    return serializing.serialize(value)


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


@dataclasses.dataclass
class EntityResolver:
    session: domains.Session
    entity: entities.Entity
    cached: Optional[str] = None

    def key(self, info, **data):
        return self.entity.key

    def serialized(self, info, **data):
        if self.cached:
            return self.cached
        assert self.entity.identity
        self.cached = serializing.serialize(
            self.entity,
            identities=info.context.identities,
        )
        return self.cached

    def diff(self, info, **data):
        return self.session.registrar.get_diff_if_available(
            self.entity.key, self.serialized(info)
        )


@query.field("world")
async def resolve_world(obj, info):
    domain = info.context.domain
    log.info("ariadne:world")
    with domain.session() as session:
        return EntityResolver(session, await session.prepare())


async def materialize(session, **kwargs):
    loaded = await session.materialize(**kwargs)
    if loaded:
        entities = [loaded]
        for other_key, other in session.registrar.entities.items():
            if other_key != loaded.key:
                entities.append(other)
        return [EntityResolver(session, e) for e in entities]
    return []


@query.field("entitiesByKey")
async def resolve_entities_by_key(obj, info, key, identities=True):
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities-by-key key=%s", key)
    with domain.session() as session:
        return await materialize(session, key=key)


@query.field("entitiesByGid")
async def resolve_entities_by_gid(obj, info, gid, identities=True):
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
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
        return [EntityResolver(session, e) for e in entities]


@query.field("people")
async def resolve_people(obj, info):
    domain = info.context.domain
    log.info("ariadne:people")
    with domain.session() as session:
        await session.prepare()
        entities = session.registrar.entities_of_klass(scopes.LivingClass)
        log.info("ariadne:people entities=%s", entities)
        return [EntityResolver(session, e) for e in entities]


subscription = ariadne.SubscriptionType()


@subscription.source("nearby")
async def nearby_generator(obj, info):
    for i in range(5):
        await asyncio.sleep(1)
        log.info("yield %s", i)
        yield [i]


@subscription.field("nearby")
def nearby_resolver(count, info):
    log.info("resolver %s", count)
    return [count[0] + 1]


mutation = ariadne.MutationType()


@dataclasses.dataclass
class Credentials:
    username: str
    password: str


class UsernamePasswordError(ValueError):
    pass


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


@dataclasses.dataclass
class PersistenceCriteria:
    read: List[str]
    write: List[str]


@dataclasses.dataclass
class LanguageQueryCriteria:
    text: str
    evaluator: str
    persistence: Optional[PersistenceCriteria] = None


def make_language_query_criteria(persistence=None, **kwargs) -> LanguageQueryCriteria:
    return LanguageQueryCriteria(
        persistence=PersistenceCriteria(**persistence) if persistence else None,
        **kwargs
    )


@dataclasses.dataclass
class Evaluation:
    reply: game.Reply
    entities: List[KeyedEntity]


@mutation.field("language")
async def resolve_language(obj, info, criteria):
    domain = info.context.domain
    parser = info.context.parser
    lqc = make_language_query_criteria(**criteria)
    log.info("ariadne:language criteria=%s", lqc)

    with domain.session() as session:
        w = await session.materialize(key=world.Key)
        assert w
        player = await session.materialize(key=lqc.evaluator)
        assert player
        tree, create_evaluator = parser.parse(lqc.text.strip())
        tree_eval = create_evaluator(w, player)
        action = tree_eval.transform(tree)
        reply = await session.perform(action, player)

        await session.save()

        return Evaluation(
            serialize_reply(reply),
            [
                EntityResolver(session, e)
                for e in session.registrar.entities.values()
                if e.modified
            ],
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

    diffs = {
        entity.Keys(row["key"]): entity.EntityUpdate(row["serialized"])
        for row in entities
    }

    await domain.store.update(diffs)

    return {"affected": len(diffs)}


def create():
    for path in ["src/dimsum/dimsum.graphql", "dimsum.graphql"]:
        if os.path.exists(path):
            type_defs = ariadne.load_schema_from_path(path)
            return ariadne.make_executable_schema(
                type_defs, [query, mutation, subscription]
            )
    raise Exception("unable to find dimsum.graphql")


@dataclasses.dataclass
class AriadneContext:
    cfg: config.Configuration
    domain: domains.Domain
    parser: grammars.ParseMultipleGrammars
    request: starlette.requests.Request
    identities: serializing.Identities = serializing.Identities.PRIVATE


def context(cfg):
    domain = cfg.make_domain()
    parser = grammars.create_parser()

    def wrap(request):
        log.info("ariadne:context %s", request)
        return AriadneContext(cfg=cfg, domain=domain, parser=parser, request=request)

    return wrap
