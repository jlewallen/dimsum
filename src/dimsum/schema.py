import asyncio
import dataclasses
import logging
import os.path
from typing import List, Optional

import ariadne
import config
import jwt
import model.domains as domains
import model.entity as entity
import model.entity as entities
import model.game as game
import model.library as library
import model.properties as properties
import model.scopes as scopes
import model.scopes.carryable as carryable
import model.scopes.users as users
import model.visual as visual
import model.world as world
import serializing
import shortuuid
import starlette.requests

# Create

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


async def materialize(
    session, key=None, gid=None, reach: Optional[int] = None, **kwargs
):
    loaded = await session.materialize(key=key, gid=gid)
    if loaded:
        entities = [loaded]
        if reach:
            for other_key, other in session.registrar.entities.items():
                if other_key != loaded.key:
                    entities.append(other)
        return [EntityResolver(session, e) for e in entities]
    return []


def flatten(l):
    return [item for sl in l for item in sl]


@query.field("entities")
async def resolve_entities(obj, info, keys, reach: int = 0, identities=True):
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities keys=%s", keys)
    with domain.session() as session:
        entities = [await materialize(session, key=key, reach=reach) for key in keys]
        return flatten(entities)


@query.field("entitiesByKey")
async def resolve_entities_by_key(obj, info, key, reach: int = 0, identities=True):
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities-by-key key=%s", key)
    with domain.session() as session:
        return await materialize(session, key=key, reach=reach)


@query.field("entitiesByGid")
async def resolve_entities_by_gid(obj, info, gid, reach: int = 0, identities=True):
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities-by-gid gid=%s", gid)
    with domain.session() as session:
        return await materialize(session, gid=gid, reach=reach)


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
async def nearby_generator(obj, info, evaluator: str):
    q: asyncio.Queue = asyncio.Queue()
    subscriptions = info.context.domain.subscriptions

    async def publish(item: visual.Renderable, **kwargs):
        await q.put(item)

    subscription = subscriptions.subscribe(evaluator, publish)

    try:
        while True:
            yield await q.get()
    finally:
        subscription.remove()


@subscription.field("nearby")
def nearby_resolver(item, info, evaluator: str):
    log.debug("resolver %s", item)
    return [serialize_reply(item)]


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
                        return dict(key=person.key, token=jwt_token)
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
    reach: int = 0
    subscription: bool = False
    persistence: Optional[PersistenceCriteria] = None


def make_language_query_criteria(
    persistence=None, reach=None, **kwargs
) -> LanguageQueryCriteria:
    return LanguageQueryCriteria(
        persistence=PersistenceCriteria(**persistence) if persistence else None,
        reach=reach if reach else 0,
        **kwargs
    )


@dataclasses.dataclass
class Evaluation:
    reply: game.Reply
    entities: List[EntityResolver]


@mutation.field("language")
async def resolve_language(obj, info, criteria):
    domain = info.context.domain
    lqc = make_language_query_criteria(**criteria)
    log.info("ariadne:language criteria=%s", lqc)

    with domain.session() as session:
        log.debug("materialize player")
        player = await session.materialize(key=lqc.evaluator)
        assert player
        log.debug("materialize world")
        w = await session.materialize(key=world.Key)
        assert w
        reply = await session.execute(player, lqc.text.strip())
        await session.save()

        async def send_entities(entities: List[EntityResolver]):
            subscriptions = info.context.domain.subscriptions
            await subscriptions.somebody(
                lqc.evaluator,
                visual.Updated(
                    entities=[
                        dict(key=row.key(info), serialized=row.serialized(info))
                        for row in entities
                    ]
                ),
            )

        entities = [
            EntityResolver(session, e)
            for e in session.registrar.entities.values()
            if e.modified or lqc.reach > 0
        ]

        if lqc.subscription:
            asyncio.create_task(send_entities(entities))
            return Evaluation(serialize_reply(reply), [])
        else:
            return Evaluation(serialize_reply(reply), entities)


@dataclasses.dataclass
class Template:
    name: str
    desc: str
    klass: str
    key: Optional[str] = None
    holding: Optional[List[str]] = None

    def generate_key(self, key_space: str) -> str:
        if self.key:
            return self.key
        return shortuuid.uuid()

    def create(self, key_space: str):
        key = self.generate_key(key_space)
        return scopes.create_klass(
            scopes.get_entity_class(self.klass),
            key=key,
            props=properties.Common(name=self.name, desc=self.desc),
        )


@mutation.field("create")
async def resolve_create(obj, info, entities):
    domain = info.context.domain
    templates = [Template(**e) for e in entities]
    key_space = "key-space"
    log.info("ariadne:create entities = %s", templates)

    with domain.session() as session:
        world = await session.prepare()
        created = [(template, template.create(key_space)) for template in templates]
        session.register([r[1] for r in created])
        by_key = {r[1].key: r[1] for r in created}
        for template, container in created:
            if template.holding:
                for k in template.holding:
                    log.debug("adding (k) %s", k)
                    e = await session.materialize(key=k)
                    log.info("adding (e) %s", e)
                    with container.make(carryable.Containing) as containing:
                        containing.add_item(e)

        await session.save()
        return Evaluation(
            game.Reply(),
            [EntityResolver(session, r[1]) for r in created],
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

        generics, area = library.create_example_world(session.world)
        session.register(generics.all)

        await session.add_area(area)
        await session.save()

        affected = [
            EntityResolver(session, e)
            for e in session.registrar.entities.values()
            if e.modified
        ]

        return {"affected": affected}


@mutation.field("update")
async def update(obj, info, entities):
    domain = info.context.domain
    log.info("ariadne:update entities=%d", len(entities))

    diffs = {
        entity.Keys(row["key"]): entity.EntityUpdate(row["serialized"])
        for row in entities
    }

    updated = await domain.store.update(diffs)

    affected = [
        dict(key=key, serialized=serialized) for key, serialized in updated.items()
    ]

    return {"affected": affected}


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
    request: starlette.requests.Request
    identities: serializing.Identities = serializing.Identities.PRIVATE


def context(cfg: config.Configuration, domain: domains.Domain):
    def wrap(request):
        log.info("ariadne:context %s", request)
        return AriadneContext(
            cfg=cfg,
            domain=domain,
            request=request,
        )

    return wrap
