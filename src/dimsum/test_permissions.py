import logging
import dataclasses
import jsondiff
import json
import functools
import shortuuid
import pytest
from typing import Any, Dict, List

import serializing
from model import *
from model.permissions import *
import test

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class ExampleObject:
    acls: Acls = dataclasses.field(
        default_factory=functools.partial(Acls, "example-object")
    )
    value: str = "Original"


@dataclasses.dataclass
class InnerObject:
    example: ExampleObject = dataclasses.field(default_factory=ExampleObject)
    value: str = "Original"


@dataclasses.dataclass
class ExampleTree:
    acls: Acls = dataclasses.field(
        default_factory=functools.partial(Acls, "example-tree")
    )
    left: InnerObject = dataclasses.field(default_factory=InnerObject)
    collection: List[InnerObject] = dataclasses.field(default_factory=list)
    value: str = "Original"


def acl_names(acls) -> List[str]:
    return [a.name for a in acls]


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
    assert acl_names(check.acls) == ["example-tree"]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_2():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.left.value = "Modified"
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == ["example-tree"]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_3():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.left.example.value = "Modified"
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    log.info("%s", before)
    log.info("%s", after)
    log.info("%s", d)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == ["example-tree", "example-object"]


@pytest.mark.asyncio
async def test_permissions_wild_json_idea_4():
    tree = ExampleTree()
    before = serializing.serialize(tree, indent=True)
    tree.collection.append(InnerObject())
    after = serializing.serialize(tree, indent=True)
    assert before and after
    d = jsondiff.diff(json.loads(before), json.loads(after), marshal=True)
    log.info("%s", before)
    log.info("%s", after)
    log.info("%s", d)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == ["example-tree"]


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
    log.info("%s", before)
    log.info("%s", after)
    log.info("%s", d)
    check = generate_security_check_from_json_diff(json.loads(before), d)
    assert acl_names(check.acls) == ["example-tree", "example-object"]


@pytest.mark.asyncio
async def test_permissions_basics():
    tw = test.TestWorld()
    await tw.initialize()

    behavior = Acls()
    assert not behavior.has(Permission.READ, "jacob")
    behavior.add(Permission.READ, "jacob")
    assert behavior.has(Permission.READ, "jacob")
    assert not behavior.has(Permission.READ, "carla")
    behavior.add(Permission.READ, "carla")
    assert behavior.has(Permission.READ, "carla")
    assert not behavior.has(Permission.READ, "tomi")
    behavior.add(Permission.READ, "*")
    assert behavior.has(Permission.READ, "tomi")

    behavior = Acls()
    owner_key = shortuuid.uuid()
    assert not behavior.has(Permission.READ, owner_key, {OwnerIdentity: owner_key})
    behavior.add(Permission.READ, OwnerIdentity)
    assert behavior.has(Permission.READ, owner_key, {OwnerIdentity: owner_key})
