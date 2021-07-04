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
import plugins.evaluation as evaluation

import test

log = logging.getLogger("dimsum.tests")

import grammars
import ast
import dynamic


@pytest.mark.asyncio
async def test_idea(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.failure("wiggle")

    with tw.domain.session() as session:
        world = await session.prepare()

        hammer = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("Hammer")),
            session=session,
        )

        with hammer.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                None,
                "b:default",
                python="""
@s.language('start: "wiggle"')
def wiggle(entity):
    log.info("wiggle: %s", entity)

@s.language('start: "burp"')
def burp(entity):
    log.info("burp: %s", entity)
""",
            )

        await session.save()

    await tw.success("hold Hammer")
    await tw.success("wiggle")
