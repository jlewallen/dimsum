import logging
import json
import pytest
import ariadne
import shortuuid
import freezegun

import config
import domains
import scopes
import serializing
from loggers import get_logger
from model import *
from schema import AriadneContext
from plugins.actions import Join
import scopes.users as users
import schema as schema_factory
import test
from test_utils import *


log = get_logger("dimsum")


def get_test_context(domain: domains.Domain, **kwargs):
    return AriadneContext(
        config.symmetrical(":memory:"),
        domain,
        None,  # type:ignore
        serializing.Identities.HIDDEN,
    )


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
    await domain.close()


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
    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_world_by_key(deterministic, snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {
        "query": '{ entitiesByKey(key: "%s", identities: false) { key serialized } }'
        % (WorldKey)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "world.json")
    await domain.close()


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
    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_language_basic(deterministic, snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        world = await session.prepare()

        welcome = scopes.area(
            key="welcome",
            props=Common(
                name="Welcome Area", desc="A two lane street in a small town."
            ),
            creator=world,
        )
        await session.add_area(welcome)
        jacob = scopes.alive(
            key="jlewallen",
            props=Common(name="Jacob"),
            creator=world,
        )
        session.register(jacob)
        await session.perform(Join(), jacob)
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
    await domain.close()


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
    await domain.close()


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
    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_login_good(deterministic):
    domain = await test.make_simple_domain(password="asdfasdf")

    data = {
        "query": 'mutation { login(credentials: { username: "jlewallen", password: "asdfasdf" }) }'
    }

    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual["data"]["login"]
    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_login_failed(deterministic, snapshot, caplog):
    domain = await test.make_simple_domain(password="asdfasdf")

    data = {
        "query": 'mutation { login(credentials: { username: "jlewallen", password: "badbadbad" }) }'
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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_update(deterministic, snapshot):
    domain = domains.Domain()

    serialized = serializing.serialize(
        World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [{"key": WorldKey, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]!) {
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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_update_and_requery(deterministic, snapshot):
    domain = domains.Domain()

    serialized = serializing.serialize(
        World(), identities=serializing.Identities.PRIVATE
    )

    data = {
        "variables": {"entities": [{"key": WorldKey, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]!) {
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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_make_sample(deterministic, snapshot):
    domain = domains.Domain(empty=True)

    serialized = serializing.serialize(
        World(), identities=serializing.Identities.PRIVATE
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

    await domain.close()


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
        "variables": {"entities": [{"key": WorldKey, "serialized": serialized}]},
        "query": """
mutation UpdateEntities($entities: [EntityDiff!]!) {
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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_entities(deterministic, snapshot):
    domain = domains.Domain()
    with domain.session() as session:
        await session.prepare()
        await session.save()

    data = {
        "query": '{ entities(keys: ["%s"], identities: false) { key serialized } }'
        % (WorldKey)
    }

    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    snapshot.assert_match(test.pretty_json(actual), "world.json")

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_create_basic(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        world = await session.prepare()
        await session.save()
        world.destroy()

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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_create_two(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        world = await session.prepare()
        await session.save()
        world.destroy()

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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_create_one_containing_another(deterministic, snapshot):
    domain = domains.Domain()

    with domain.session() as session:
        world = await session.prepare()
        await session.save()
        world.destroy()

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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_redeem_invite(deterministic):
    domain = await test.make_simple_domain(password="asdfasdf")

    with domain.session() as session:
        world = await session.prepare()
        jacob_key = await users.lookup_username(world, "jlewallen")
        jacob = await session.materialize(key=jacob_key)
        invite_url, invite_token = jacob.make(users.Auth).invite("hunter42")

    data = {
        "query": 'mutation { login(credentials: { username: "carla@carla.com", password: "asdfasdf", token: "%s", secret: "hunter42" }) }'
        % (invite_token,)
    }
    ok, actual = await ariadne.graphql(
        schema, data, context_value=get_test_context(domain)
    )
    assert ok
    assert actual["data"]["login"]

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_redeem_invite_bad_secret(deterministic, caplog):
    domain = await test.make_simple_domain(password="asdfasdf")

    with domain.session() as session:
        world = await session.prepare()
        jacob_key = await users.lookup_username(world, "jlewallen")
        jacob = await session.materialize(key=jacob_key)
        invite_url, invite_token = jacob.make(users.Auth).invite("hunter42")

    data = {
        "query": 'mutation { login(credentials: { username: "carla@carla.com", password: "asdfasdf", token: "%s", secret: "hunter43" }) }'
        % (invite_token,)
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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_correct_version_in_modified_return(
    deterministic, caplog, snapshot
):
    domain = await test.make_simple_domain()

    with domain.session() as session:
        world = await session.prepare()
        jacob_key = await users.lookup_username(world, "jlewallen")
        jacob = await session.materialize(key=jacob_key)
        invite_url, invite_token = jacob.make(users.Auth).invite("hunter42")

    data = {
        "query": """
mutation {
    language(criteria: { text: "edit help", evaluator: "%s", reach: 1 }) {
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

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_compare_and_swap_invalid_previous(
    deterministic, snapshot, caplog
):
    domain = await test.make_simple_domain()

    data = {
        "variables": {
            "entities": [
                {
                    "key": WorldKey,
                    "paths": [
                        {
                            "path": "props.map.name.value",
                            "previous": json.dumps("Not World"),
                            "value": json.dumps("Super Duper World"),
                        }
                    ],
                }
            ]
        },
        "query": """
mutation CompareAndSwap($entities: [EntityCompareAndSwap!]!) {
    compareAndSwap(entities: $entities) {
        affected {
            key
            serialized
        }
    }
}
""",
    }

    with caplog.at_level(logging.CRITICAL, logger="dimsum"):
        with caplog.at_level(logging.CRITICAL, logger="ariadne.errors.hidden"):
            ok, actual = await ariadne.graphql(
                schema,
                data,
                debug=True,
                context_value=get_test_context(domain),
                logger="ariadne.errors.hidden",
            )
            assert ok
            snapshot.assert_match(
                test.pretty_json(actual, deterministic=True), "response.json"
            )

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_compare_and_swap_valid_previous(deterministic, snapshot):
    domain = await test.make_simple_domain()

    data = {
        "variables": {
            "entities": [
                {
                    "key": WorldKey,
                    "paths": [
                        {
                            "path": "props.map.name.value",
                            "previous": json.dumps("World"),
                            "value": json.dumps("Super Duper World"),
                        }
                    ],
                }
            ]
        },
        "query": """
mutation CompareAndSwap($entities: [EntityCompareAndSwap!]!) {
    compareAndSwap(entities: $entities) {
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
    snapshot.assert_match(test.pretty_json(actual, deterministic=True), "response.json")

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_compare_and_swap_brand_new_path_value(deterministic, snapshot):
    domain = await test.make_simple_domain()

    data = {
        "variables": {
            "entities": [
                {
                    "key": WorldKey,
                    "paths": [
                        {
                            "path": "scopes.encyclopedia.body",
                            "previous": json.dumps(None),
                            "value": json.dumps("Hello, world!"),
                        }
                    ],
                }
            ]
        },
        "query": """
mutation CompareAndSwap($entities: [EntityCompareAndSwap!]!) {
    compareAndSwap(entities: $entities) {
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
    snapshot.assert_match(test.pretty_json(actual, deterministic=True), "response.json")

    await domain.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_graphql_compare_and_swap_replace_behavior(
    caplog, deterministic, snapshot
):
    domain = await test.make_simple_domain()

    box_key = shortuuid.uuid()

    with domain.session() as session:
        world = await session.prepare()

        box = scopes.item(
            key=box_key,
            creator=world,
            props=Common(name="Box"),
        )

        session.register(box)

        welcome = await session.materialize(key="welcome")
        assert welcome

        await session.save()

    data = {
        "variables": {
            "entities": [
                {
                    "key": box_key,
                    "paths": [
                        {
                            "path": "scopes.behaviors.behaviors.map.b:default",
                            "value": json.dumps(
                                {
                                    "py/object": "scopes.behavior.Behavior",
                                    "python": 'og.info("fail")',
                                }
                            ),
                        },
                    ],
                }
            ]
        },
        "query": """
mutation CompareAndSwap($entities: [EntityCompareAndSwap!]!) {
    compareAndSwap(entities: $entities) {
        affected {
            key
            serialized
        }
    }
}
""",
    }

    with caplog.at_level(logging.CRITICAL, logger="dimsum.dynamic.errors"):
        with caplog.at_level(logging.CRITICAL, logger="ariadne.errors.hidden"):
            ok, actual = await ariadne.graphql(
                schema,
                data,
                context_value=get_test_context(domain),
                logger="ariadne.errors.hidden",
            )
            assert ok
            snapshot.assert_match(
                test.pretty_json(actual, deterministic=True), "response.json"
            )

    await domain.close()
