import pytest
import freezegun
import logging
import base64
import json
import ariadne

import model.properties as properties
import model.world as world
import model.domains as domains
import model.scopes.users as users
import model.scopes as scopes
import plugins.default.actions as actions

import serializing
import config
import grammars
import bus
import test

import schema as schema_factory
from schema import AriadneContext
from graphql import GraphQLError

log = logging.getLogger("dimsum")


def get_test_context(domain: domains.Domain, **kwargs):
    subscriptions = bus.SubscriptionManager()

    return AriadneContext(
        config.symmetrical(":memory:"),
        domain,
        subscriptions,
        grammars.create_parser(),
        None,  # type:ignore
        serializing.Identities.HIDDEN,
    )


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_ariadne_basic(snapshot):
    query = ariadne.QueryType()

    @query.field("hello")
    def resolve_hello(obj, info):
        return "Hello!"

    type_defs = ariadne.gql(
        """
schema {
    query: Query
}

type Query {
	hello: String!
}
"""
    )
    schema = ariadne.make_executable_schema(type_defs, query)

    data = {"query": "{ hello }"}
    ok, actual = await ariadne.graphql(schema, data)
    assert ok


schema = schema_factory.create()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_size(snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {"query": "{ size }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual == {"data": {"size": 1}}


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_directly(snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {"query": "{ world { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_by_key(snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {
        "query": '{ entitiesByKey(key: "%s", identities: false) { key serialized } }'
        % (world.Key)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_by_gid(snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        world = await session.prepare()
        assert world.props.gid == 0
        await session.save()

    data = {
        "query": "{ entitiesByGid(gid: %d, identities: false) { key serialized } }"
        % (0)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_language_basic(snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        world = await session.prepare()

        welcome = scopes.area(
            key="welcome",
            props=properties.Common(name="welcome"),
            creator=world,
        )
        await session.add_area(welcome)
        jacob = scopes.alive(
            key="jlewallen",
            props=properties.Common(name="Jacob"),
            creator=world,
        )
        session.register(jacob)
        await session.perform(actions.Join(), jacob)
        await session.save()

    data = {
        "query": """
mutation {
    language(criteria: { text: "look", evaluator: "%s" }) {
        reply
        entities { key serialized }
    }
}
"""
        % jacob.key
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "entities.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities_areas(snapshot):
    domain = await test.make_simple_domain()

    data = {"query": "{ areas { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "areas.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities_people(snapshot):
    domain = await test.make_simple_domain()

    data = {"query": "{ people { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "people.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_login_good():
    domain = await test.make_simple_domain(password="asdfasdf")
    jacob_key = base64.b64encode("jlewallen".encode("utf-8")).decode("utf-8")

    data = {
        "query": 'mutation { login(credentials: { username: "%s", password: "asdfasdf" }) }'
        % (jacob_key,)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual["data"]["login"]


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_login_failed(caplog, snapshot):
    domain = await test.make_simple_domain(password="asdfasdf")
    jacob_key = base64.b64encode("jlewallen".encode("utf-8")).decode("utf-8")

    data = {
        "query": 'mutation { login(credentials: { username: "%s", password: "badbadbad" }) }'
        % (jacob_key,)
    }

    with caplog.at_level(logging.CRITICAL, logger="ariadne.errors.hidden"):
        ok, actual = await ariadne.graphql(
            schema,
            data,
            debug=True,
            context_value=get_test_context(domain),
            logger="ariadne.errors.hidden",
        )
        assert ok
        assert "schema.UsernamePasswordError" in json.dumps(actual, indent=4)


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_update():
    domain = domains.Domain()

    serialized = serializing.serialize(
        world.World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [{"key": world.Key, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]) {
    update(entities: $entities) {
        affected
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual == {"data": {"update": {"affected": 1}}}


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_update_and_requery(snapshot):
    domain = domains.Domain()

    serialized = serializing.serialize(
        world.World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [{"key": world.Key, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]) {
    update(entities: $entities) {
        affected
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual == {"data": {"update": {"affected": 1}}}

    data = {"query": "{ world { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_make_sample(snapshot):
    domain = domains.Domain(empty=True)

    serialized = serializing.serialize(
        world.World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [serialized]},
        "query": "mutation { makeSample { affected } }",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual == {"data": {"makeSample": {"affected": 59}}}

    data = {"query": "{ world { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_delete(snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        await session.prepare()
        await session.save()

        session.world.destroy()

        serialized = serializing.serialize(
            session.world, identities=serializing.Identities.PRIVATE
        )

    data = {
        "variables": {"entities": [{"key": world.Key, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]) {
    update(entities: $entities) {
        affected
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(json.dumps(actual, indent=4), "response.json")
