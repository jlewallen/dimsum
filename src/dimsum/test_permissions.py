import dataclasses
import jsondiff
import json
import functools
import shortuuid
import pytest
from itertools import groupby
from typing import Any, Dict, List, Optional

import serializing
import tools
from model import *
from model.permissions import *
import test


@dataclasses.dataclass
class ExampleObject:
    acls: Acls = dataclasses.field(default_factory=functools.partial(Acls))
    value: str = "Original"


@dataclasses.dataclass
class InnerObject:
    example: ExampleObject = dataclasses.field(default_factory=ExampleObject)
    value: str = "Original"


@dataclasses.dataclass
class ExampleTree:
    acls: Acls = dataclasses.field(default_factory=functools.partial(Acls))
    left: InnerObject = dataclasses.field(default_factory=InnerObject)
    collection: List[InnerObject] = dataclasses.field(default_factory=list)
    value: str = "Original"


def acl_names(acls: Dict[str, Acls]) -> List[str]:
    return [key for key, _ in acls.items()]


@dataclasses.dataclass
class SecurityCheckBuilder:
    pass


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_1():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.value = "Modified"
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == [""]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_2():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.left.value = "Modified"
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == [""]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_3():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.left.example.value = "Modified"
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == ["", "left.example"]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_4():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.collection.append(InnerObject())
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == [""]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_5():
    tree = ExampleTree()
    tree.collection.append(InnerObject())
    tree.collection.append(InnerObject())
    tree.collection.append(InnerObject())
    before = serializing.serialize(tree, indent=True)
    tree.collection[1].example.value = "Modified"
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == ["", "collection.1.example"]


@pytest.mark.asyncio
async def test_permissions_basics():
    tw = test.TestWorld()
    await tw.initialize()

    behavior = Acls()
    assert not behavior.has(Permission.READ, SecurityContext("jacob"))
    behavior.add(Permission.READ, "jacob")
    assert behavior.has(Permission.READ, SecurityContext("jacob"))
    assert not behavior.has(Permission.READ, SecurityContext("carla"))
    behavior.add(Permission.READ, "carla")
    assert behavior.has(Permission.READ, SecurityContext("carla"))
    assert not behavior.has(Permission.READ, SecurityContext("tomi"))
    behavior.add(Permission.READ, "*")
    assert behavior.has(Permission.READ, SecurityContext("tomi"))

    behavior = Acls()
    owner_key = shortuuid.uuid()
    assert not behavior.has(
        Permission.READ, SecurityContext(owner_key, {SecurityMappings.Owner: owner_key})
    )
    behavior.add(Permission.READ, SecurityMappings.Owner)
    assert behavior.has(
        Permission.READ, SecurityContext(owner_key, {SecurityMappings.Owner: owner_key})
    )


def get_test_security_context(person: Entity, entity: Entity):
    return tools.get_entity_security_context(
        tools.get_person_security_context(person), entity
    )


@pytest.mark.asyncio
async def test_permissions_save_create_thing_hands_hold():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)

        assert await session.execute(jacob, "create thing Box")

        await session.save(functools.partial(get_test_security_context, jacob))


@pytest.mark.asyncio
async def test_permissions_save_create_thing_hands_drop_jacob():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)

        assert await session.execute(jacob, "create thing Box")
        assert await session.execute(jacob, "drop Box")

        await session.save(functools.partial(get_test_security_context, jacob))


@pytest.mark.asyncio
async def test_permissions_save_create_thing_hands_drop_carla():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()

    with tw.domain.session() as session:
        world = await session.prepare()
        carla = await session.materialize(key=tw.carla_key)

        assert await session.execute(carla, "create thing Box")
        assert await session.execute(carla, "drop Box")

        await session.save(functools.partial(get_test_security_context, carla))
