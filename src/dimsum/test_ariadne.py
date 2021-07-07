from typing import Dict, Any, List

import logging
import base64
import json
import freezegun
import pytest

import model.crypto as crypto
import model.entity as entity
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

import ariadne
import schema as schema_factory
from schema import AriadneContext
from graphql import GraphQLError

log = logging.getLogger("dimsum")


def get_test_context(domain: domains.Domain, **kwargs):
    return AriadneContext(
        config.symmetrical(":memory:"),
        domain,
        None,  # type:ignore
        serializing.Identities.HIDDEN,
    )


@pytest.fixture(scope="function")
def deterministic():
    with test.Deterministic():
        yield


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_ariadne_basic(deterministic, snapshot):
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
async def test_graphql_size(deterministic, snapshot):
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
async def test_graphql_world_directly(deterministic, snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {"query": "{ world { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_by_key(deterministic, snapshot):
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
    snapshot.assert_match(test.pretty_json(actual), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_by_gid(deterministic, snapshot):
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
    snapshot.assert_match(test.pretty_json(actual), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_language_basic(deterministic, snapshot):
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
    snapshot.assert_match(test.pretty_json(actual), "entities.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities_areas(deterministic, snapshot):
    domain = await test.make_simple_domain()

    data = {"query": "{ areas { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "areas.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities_people(deterministic, snapshot):
    domain = await test.make_simple_domain()

    data = {"query": "{ people { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "people.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_login_good(deterministic):
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
async def test_graphql_login_failed(deterministic, snapshot, caplog):
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
async def test_graphql_update(deterministic, snapshot):
    domain = domains.Domain()

    serialized = serializing.serialize(
        world.World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [{"key": world.Key, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]) {
    update(entities: $entities) {
        affected {
            key
            serialized
        }
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "response.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_update_and_requery(deterministic, snapshot):
    domain = domains.Domain()

    serialized = serializing.serialize(
        world.World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [{"key": world.Key, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]) {
    update(entities: $entities) {
        affected { key serialized }
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "response.json")

    data = {"query": "{ world { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_make_sample(deterministic, snapshot):
    domain = domains.Domain(empty=True)

    serialized = serializing.serialize(
        world.World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [serialized]},
        "query": "mutation { makeSample { affected { key serialized } } }",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "make_response.json")

    data = {"query": "{ world { key serialized } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_delete(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        await session.prepare()
        await session.save()

        assert session.world
        session.world.destroy()

        serialized = serializing.serialize(
            session.world, identities=serializing.Identities.PRIVATE
        )

    data = {
        "variables": {"entities": [{"key": world.Key, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]) {
    update(entities: $entities) {
        affected { key serialized }
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "response.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities(deterministic, snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {
        "query": '{ entities(keys: ["%s"], identities: false) { key serialized } }'
        % (world.Key)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_create_basic(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        await session.prepare()
        await session.save()

        assert session.world
        session.world.destroy()

    data = {
        "variables": {"key": "asdfasdf", "name": "Flute"},
        "query": """
mutation CreateThing($key: String!, $name: String!) {
    create(entities: [{ key: $key, name: $name, desc: $name, klass: "ItemClass" }]) {
        entities {
            key
            serialized
        }
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "response.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_create_two(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        await session.prepare()
        await session.save()

        assert session.world
        session.world.destroy()

    data = {
        "variables": {
            "entities": [
                dict(key="a", name="Thing A", desc="Thing", klass="ItemClass"),
                dict(key="b", name="Thing B", desc="Thing", klass="ItemClass"),
            ]
        },
        "query": """
mutation CreateThing($entities: [EntityTemplate!]) {
    create(entities: $entities) {
        entities {
            key
            serialized
        }
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "response.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_create_one_containing_another(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        await session.prepare()
        await session.save()

        assert session.world
        session.world.destroy()

    data = {
        "variables": {
            "entities": [
                dict(
                    key="a",
                    name="Thing A",
                    desc="Thing",
                    klass="ItemClass",
                    holding=["b"],
                ),
                dict(key="b", name="Thing B", desc="Thing", klass="ItemClass"),
            ]
        },
        "query": """
mutation CreateThing($entities: [EntityTemplate!]) {
    create(entities: $entities) {
        entities {
            key
            serialized
        }
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "response.json")
