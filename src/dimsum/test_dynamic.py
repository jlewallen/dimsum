from typing import Callable, List, Dict, Optional, Any

import sys
import logging
import dataclasses
import pytest

import model.game as game
import model.properties as properties
import model.world as world
import model.entity as entity
import model.reply as reply

import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable
import model.scopes.behavior as behavior
import model.scopes as scopes

import plugins.actions as actions

import grammars
import ast
import dynamic

import test

log = logging.getLogger("dimsum.tests")


async def add_behaviored_thing(tw: test.TestWorld, name: str, python: str):
    with tw.domain.session() as session:
        world = await session.prepare()

        item = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common(name)),
            session=session,
        )

        with item.make(behavior.Behaviors) as behave:
            behave.add_behavior(None, "b:default", python=python)

        await session.save()

        return item


@pytest.mark.asyncio
async def test_multiple_simple_verbs(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.failure("wiggle")

    hammer = await add_behaviored_thing(
        tw,
        "Hammer",
        """
@language('start: "wiggle"')
def wiggle(entity, say=None):
    log.info("wiggle: %s", entity)
    return "hey there!"

@language('start: "burp"')
def burp(entity, say=None):
    log.info("burp: %s", entity)
    return "hey there!"
""",
    )

    await tw.success("hold Hammer")
    await tw.success("wiggle")
    await tw.success("burp")


@pytest.mark.asyncio
async def test_dynamic_applies_only_when_held(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    hammer = await add_behaviored_thing(
        tw,
        "Hammer",
        """
@language('start: "wiggle"', condition=Held())
def wiggle(entity, say=None):
    log.info("wiggle: %s", entity)
    return "hey there!"
""",
    )

    await tw.failure("wiggle")
    await tw.success("hold Hammer")
    await tw.success("wiggle")


@pytest.mark.asyncio
async def test_dynamic_say_everyone(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    hammer = await add_behaviored_thing(
        tw,
        "Keys",
        """
@language('start: "jingle"', condition=Held())
def jingle(entity, say=None):
    log.info("jingle: %s", entity)
    say.nearby("you hear kings jingling")
    return "hey there!"
""",
    )

    await tw.success("hold Keys")
    await tw.success("jingle")
