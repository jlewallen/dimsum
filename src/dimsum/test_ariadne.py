import pytest
import freezegun
import logging
import ariadne
import base64

import model.properties as properties
import model.world as world
import model.domains as domains
import model.scopes as scopes
import default.actions as actions

import config
import test

import schema as schema_factory
from schema import AriadneContext


log = logging.getLogger("dimsum")


def get_test_context(domain: domains.Domain, **kwargs):
    return AriadneContext(domain, config.Configuration("test.sqlite3", "session-key"))


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

    data = {"query": "{ size }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual == {"data": {"size": 1}}


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world(snapshot):
    domain = domains.Domain()

    data = {"query": "{ world }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(actual["data"]["world"], "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_by_key(snapshot):
    domain = domains.Domain()

    data = {"query": '{ entities(key: "%s") }' % (world.Key)}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match("\n".join(actual["data"]["entities"]), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_language_basic(snapshot):
    domain = domains.Domain()
    welcome = scopes.area(
        key="welcome", props=properties.Common(name="welcome"), creator=domain.world
    )
    domain.add_area(welcome)
    jacob = scopes.alive(
        key="jlewallen", props=properties.Common(name="Jacob"), creator=domain.world
    )
    domain.registrar.register(jacob)
    await domain.perform(actions.Join(), jacob)

    data = {
        "query": '{ language(criteria: { text: "look", evaluator: "%s" }) { reply entities } }'
        % jacob.key
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(
        "\n".join(actual["data"]["language"]["entities"]), "entities.json"
    )


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities_areas(snapshot):
    domain = await test.make_simple_domain()

    data = {"query": "{ areas }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match("\n".join(actual["data"]["areas"]), "areas.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities_people(snapshot):
    domain = await test.make_simple_domain()

    data = {"query": "{ people }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match("\n".join(actual["data"]["people"]), "people.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_login():
    domain = await test.make_simple_domain(password="asdfasdf")
    jacob_key = base64.b64encode("jlewallen".encode("utf-8")).decode("utf-8")

    data = {
        "query": '{ login(credentials: { username: "%s", password: "asdfasdf" }) }'
        % (jacob_key,)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
