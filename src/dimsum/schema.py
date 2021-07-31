import asyncio
import dataclasses
import os.path
import shortuuid
import starlette.requests
import ariadne
import functools
import jwt
import json
import jsondiff
from typing import List, Optional, Dict, Any, Union

import config
import domains
import dynamic
import serializing
import scopes
import library
import tools
from loggers import get_logger
from model import (
    Entity,
    World,
    CompiledJson,
    WorldKey,
    Serialized,
    Renderable,
    Reply,
    Updated,
    Common,
    EntityConflictException,
)
from plugins.actions import Join
from plugins.admin import lookup_username, register_username
import plugins.admin as admin
import scopes.carryable as carryable
import scopes.behavior as behavior
import scopes.users as users


log = get_logger("dimsum")


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
    log.debug("ariadne:reply %s", value)
    serialized = serializing.serialize(value)
    if isinstance(value, Renderable):
        return dict(rendered=json.dumps(value.render_tree()), model=serialized)
    return dict(model=serialized)


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
    entity: Entity
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
        return self.session.registrar.get_diff_if_available(self.entity.key)


def verify_token(info) -> Optional[str]:
    if info.context.request is None:
        return None
    headers = info.context.request.headers
    if "Authorization" not in headers:
        raise Exception("unauthorized (header)")
    try:
        token = headers["Authorization"].split(" ")[1]
        decoded = jwt.decode(token, info.context.cfg.session_key, algorithms=["HS256"])
        return decoded["key"]
    except:
        log.exception("token", exc_info=True)
        raise Exception("unauthorized")


@query.field("world")
async def resolve_world(obj, info):
    verify_token(info)
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
    verify_token(info)
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities keys=%s", keys)
    with domain.session() as session:
        entities = flatten(
            [await materialize(session, key=key, reach=reach) for key in keys]
        )
        log.info("ariadne:entities nentities=%d", len(entities))
        return entities


@query.field("entitiesByKey")
async def resolve_entities_by_key(obj, info, key, reach: int = 0, identities=True):
    verify_token(info)
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities-by-key key=%s", key)
    with domain.session() as session:
        return await materialize(session, key=key, reach=reach)


@query.field("entitiesByGid")
async def resolve_entities_by_gid(obj, info, gid, reach: int = 0, identities=True):
    verify_token(info)
    domain = info.context.domain
    info.context.identities = (
        serializing.Identities.PRIVATE if identities else serializing.Identities.HIDDEN
    )
    log.info("ariadne:entities-by-gid gid=%s", gid)
    with domain.session() as session:
        return await materialize(session, gid=gid, reach=reach)


@query.field("areas")
async def resolve_areas(obj, info):
    verify_token(info)
    domain = info.context.domain
    log.info("ariadne:areas")
    with domain.session() as session:
        await session.prepare()
        entities = session.registrar.entities_of_klass(scopes.AreaClass)
        log.info("ariadne:areas nentities=%d", len(entities))
        return [EntityResolver(session, e) for e in entities]


@query.field("people")
async def resolve_people(obj, info):
    verify_token(info)
    domain = info.context.domain
    log.info("ariadne:people")
    with domain.session() as session:
        await session.prepare()
        entities = session.registrar.entities_of_klass(scopes.LivingClass)
        log.info("ariadne:people nentities=%d", len(entities))
        return [EntityResolver(session, e) for e in entities]


subscription = ariadne.SubscriptionType()


@subscription.source("nearby")
async def nearby_generator(
    obj, info, evaluator: Optional[str] = None, token: Optional[str] = None
):
    assert token

    decoded = jwt.decode(token, info.context.cfg.session_key, algorithms=["HS256"])

    log.info("decoded=%s", decoded)

    evaluator = decoded["key"]

    log.debug("evaluator=%s", evaluator)

    q: asyncio.Queue = asyncio.Queue()
    subscriptions = info.context.domain.subscriptions

    async def publish(item: Renderable, **kwargs):
        await q.put(item)

    subscription = subscriptions.subscribe(evaluator, publish)

    try:
        while True:
            yield await q.get()
    finally:
        subscription.remove()


@subscription.field("nearby")
def nearby_resolver(
    item, info, evaluator: Optional[str] = None, token: Optional[str] = None
):
    log.debug("resolver %s", item)
    return [serialize_reply(item)]


mutation = ariadne.MutationType()


@dataclasses.dataclass
class Credentials:
    username: str
    password: str
    token: Optional[str] = None
    secret: Optional[str] = None


class UsernamePasswordError(ValueError):
    pass


@mutation.field("login")
async def login(obj, info, credentials):
    domain = info.context.domain
    creds = Credentials(**credentials)
    log.info("ariadne:login username=%s", creds.username)
    with domain.session() as session:
        world = await session.prepare()

        if creds.token and creds.secret:
            log.info("verifying invite")
            decoded = jwt.decode(
                creds.token, users.invite_session_key, algorithms=["HS256"]
            )

            # verify secret against stored
            secured = decoded["password"]
            if not users.try_password(secured, creds.secret):
                raise UsernamePasswordError("invalid secret")

            log.info("decoded=%s", decoded)
            creator = await session.materialize(key=decoded["creator"])
            assert creator

            maybe_key = await lookup_username(world, creds.username)
            if maybe_key:
                raise UsernamePasswordError("username taken")

            # everything looks good
            person = scopes.alive(
                creator=session.world,
                props=Common(creds.username, desc="A player", invited_by=creator.key),
            )
            await register_username(world, creds.username, person.key)
            await session.perform(Join(), person)
            await session.perform(admin.Auth(password=creds.password), person)
            await session.save()

            token = dict(key=person.key)
            jwt_token = jwt.encode(
                token, info.context.cfg.session_key, algorithm="HS256"
            )

            return dict(key=person.key, token=jwt_token)

        try:
            maybe_key = await lookup_username(world, creds.username)
            if not maybe_key:
                raise UsernamePasswordError()

            people = await session.try_materialize(key=maybe_key)
            if person := people.maybe_one():
                with person.make(users.Auth) as auth:
                    if auth.try_password(creds.password):
                        token = dict(key=person.key)
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
        **kwargs,
    )


@dataclasses.dataclass
class Evaluation:
    reply: Reply
    entities: List[EntityResolver]


@mutation.field("language")
async def resolve_language(obj, info, criteria):
    auth_key = verify_token(info)
    domain = info.context.domain
    lqc = make_language_query_criteria(**criteria)
    evaluator = auth_key or lqc.evaluator
    log.info("ariadne:language criteria=%s", lqc)

    with domain.session() as session:
        log.debug("materialize world")
        w = await session.prepare()
        assert w
        log.debug("materialize player=%s", evaluator)
        player = await session.materialize(key=evaluator)
        assert player
        reply = await session.execute(player, lqc.text.strip())

        def get_security_context(person: Entity, entity: Entity):
            return tools.get_entity_security_context(
                tools.get_person_security_context(person), entity
            )

        modified_keys = await session.save(
            functools.partial(get_security_context, player)
        )

        async def send_entities(entities: List[EntityResolver]):
            subscriptions = info.context.domain.subscriptions
            await subscriptions.somebody(
                evaluator,
                Updated(
                    entities=[
                        dict(key=row.key(info), serialized=row.serialized(info))
                        for row in entities
                    ]
                ),
            )

        log.debug(
            "ariadne:language materialized=%d", len(session.registrar.entities.values())
        )

        entities = [
            EntityResolver(session, e)
            for e in session.registrar.entities.values()
            if e.modified or lqc.reach > 0
        ]

        log.info("ariadne:language nentities=%d", len(entities))

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
            props=Common(name=self.name, desc=self.desc),
        )


@mutation.field("create")
async def resolve_create(obj, info, entities):
    auth_key = verify_token(info)
    domain = info.context.domain
    templates = [Template(**e) for e in entities]
    key_space = "key-space"
    log.info("ariadne:create entities=%s", templates)

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

        if auth_key:
            person = await session.materialize(key=auth_key)
            assert person

            def get_security_context(person: Entity, entity: Entity):
                return tools.get_entity_security_context(
                    tools.get_person_security_context(person), entity
                )

            await session.save(functools.partial(get_security_context, person))
        else:
            await session.save()

        return Evaluation(
            Reply(),
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
    auth_key = verify_token(info)
    domain = info.context.domain
    log.info("ariadne:make-sample")

    with domain.session() as session:
        world = await session.prepare()
        factory = library.example_world_factory(world)
        await factory(session)
        await session.save()

        affected = [
            EntityResolver(session, e)
            for e in session.registrar.entities.values()
            if e.modified
        ]

        return {"affected": affected}


@mutation.field("update")
async def update(obj, info, entities):
    verify_token(info)
    domain = info.context.domain
    log.info("ariadne:update entities=%d", len(entities))

    serialized = [Serialized(row["key"], row["serialized"]) for row in entities]
    if len(serialized) == 0:
        return {"affected": []}

    with domain.session() as session:
        world = await session.prepare()

        # TODO asyncio.gather
        log.info("update: loading %s", [row.key for row in serialized])
        before = [await session.try_materialize(key=row.key) for row in serialized]

        log.info("update: materializing")
        incoming = await session.try_materialize(json=serialized)
        for e in incoming.entities:
            e.touch()
        log.info("update: incoming=%s", incoming)

        modified_keys = await session.save()
        affected = [
            EntityResolver(session, await session.materialize(key=key))
            for key in modified_keys
        ]

        return {"affected": affected}


def make_diff(path: str, value: Union[None, str, Dict[str, Any]]):
    keys = path.split(".")
    diff: Dict[str, Any] = {}
    curr = diff
    for key in keys[:-1]:
        curr[key] = {}
        curr = curr[key]
    curr[keys[-1]] = value
    return diff


def is_only_path_being_added(path: str, diff: Dict[str, Any]) -> bool:
    """This checks for the scenario where a new path is being inserted
    into some JSON and so the diff, when comparing to the previous
    value basically fills in the path with a null. We ignore these non-empty diffs."""
    sub_diff = jsondiff.diff(make_diff(path, None), diff)
    return sub_diff == {}


def is_acceptable_non_empty_diff(path: str, diff: Dict[str, Any]) -> bool:
    return is_only_path_being_added(path, diff)


@mutation.field("compareAndSwap")
async def compare_and_swap(obj, info, entities):
    verify_token(info)
    domain = info.context.domain
    log.info("ariadne:cas entities=%s", entities)
    if len(entities) == 0:
        return {"affected": []}

    with domain.session() as session:
        world = await session.prepare()

        # Multiple entities can be updated in a single transaction,
        # loop over them and the path changes that are being
        # attempted.
        for row in entities:
            key = row["key"]
            log.info("materialize key=%s", key)
            entity = await session.materialize(key=key)
            original = session.registrar.get_original_if_available(key)
            assert original

            compiled: CompiledJson = original.compiled
            was_behavior_modified = False

            # We allow multiple paths to be updated per entity.
            for change in row["paths"]:
                path = change["path"]
                if behavior.DefaultKey in path:
                    was_behavior_modified = True
                try:
                    # We're given JSON strings with the previous value
                    # and the value being written. Parse them here.
                    parsed_previous = (
                        json.loads(change["previous"]) if "previous" in change else None
                    )
                    parsed_value = json.loads(change["value"])

                    log.debug("%s: cas: '%s' = %s", key, path, parsed_previous)
                    log.debug("%s: cas: '%s' = %s", key, path, parsed_value)

                    if parsed_previous:
                        # Create a JSON diff object that recreates the
                        # object in its original before state. This is
                        # basically an easy way to set the given path to
                        # the previous value. The idea here is that this
                        # should be the same JSON before and after if
                        # we're to continue with the update.
                        to_previous = make_diff(path, parsed_previous)
                        previous = jsondiff.patch(compiled, to_previous)
                        diff_from_expected = jsondiff.diff(compiled, previous)
                        if (
                            diff_from_expected != {}
                            and not is_acceptable_non_empty_diff(
                                path, diff_from_expected
                            )
                        ):
                            log.info("%s: cas '%s' = %s", key, path, parsed_previous)
                            log.info("%s: cas '%s' = %s", key, path, parsed_value)
                            log.info("%s: cas before: %s", key, compiled)
                            log.info("%s: cas after: %s", key, previous)
                            log.info("%s: cas unexpected: %s", key, diff_from_expected)
                            raise EntityConflictException()

                    # Everything looks fine, so create a new JSON diff
                    # to update the path to the new value and then
                    # apply that before loading that into the session
                    # as the updated entity.
                    to_value = make_diff(path, parsed_value)
                    compiled = jsondiff.patch(compiled, to_value)
                except:
                    log.error("compare-swap failed: patch=%s", change)
                    raise

            # Reload with the accumulated changes.
            entity = await session.materialize(
                json=[Serialized(key, json.dumps(compiled))]
            )

            entity.touch()

            # If behavior was modified, then verify that behavior.
            if was_behavior_modified:
                contributing = tools.get_contributing_entities(world, entity)
                log.info("%s: verifying behavior %s", key, contributing)
                async with dynamic.Behavior(
                    dynamic.LogDynamicCalls(), contributing
                ) as db:
                    await db.verify()

        # Save all our changes and return the affected entities.
        modified_keys = await session.save()
        affected = [
            EntityResolver(session, await session.materialize(key=key))
            for key in modified_keys
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
        log.debug("ariadne:context %s", request)
        return AriadneContext(
            cfg=cfg,
            domain=domain,
            request=request,
        )

    return wrap
