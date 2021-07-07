import logging

import ariadne
import brokers.schema as schema_factory
from brokers.schema import AriadneContext
import freezegun
import pytest
import routing

log = logging.getLogger("dimsum")


def get_test_context(broker: routing.Broker, **kwargs):
    return AriadneContext(broker, None)  # type:ignore


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
async def test_query_targets_empty(snapshot):
    broker = routing.Broker()

    data = {"query": "{ targets { name } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(broker)
    )
    assert ok
    assert actual == {"data": {"targets": []}}


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_provision_process(snapshot):
    broker = routing.Broker()

    data = {
        "variables": {"config": {"name": "default", "process": {"command": "cat"}}},
        "query": """
mutation Provision($config: TargetConfiguration!) {
    provision(config: $config) {
        name
    }
}
""",
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(broker)
    )
    assert ok
    assert actual == {"data": {"provision": {"name": "default"}}}

    data = {"query": "{ targets { name } }"}
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(broker)
    )
    assert ok
