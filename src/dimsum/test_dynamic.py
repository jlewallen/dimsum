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
            behave.add_behavior(world, python=python)

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
async def wiggle(entity, person=None, say=None):
    log.info("wiggle: %s", entity)
    return "hey there!"

@language('start: "burp"')
async def burp(entity, person=None, say=None):
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
async def wiggle(entity, person=None, say=None):
    log.info("wiggle: %s", entity)
    return "hey there!"
""",
    )

    await tw.failure("wiggle")
    await tw.success("hold Hammer")
    await tw.success("wiggle")


@pytest.mark.asyncio
async def test_dynamic_say_nearby(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    hammer = await add_behaviored_thing(
        tw,
        "Keys",
        """
@language('start: "jingle"', condition=Held())
async def jingle(entity, person=None, say=None):
    log.info("jingle: %s", entity)
    say.nearby("you hear kings jingling")
    return "hey there!"
""",
    )

    await tw.success("hold Keys")
    await tw.success("jingle")


@pytest.mark.asyncio
async def test_dynamic_smash(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await add_behaviored_thing(
        tw,
        "Nail",
        """
@dataclass(frozen=True)
class Smashed(Event):
    smasher: Entity
    smashed: Entity

@received(Smashed)
async def smashed(entity: Entity, ev: Smashed, say=None):
    log.info("smashed! %s", ev)
    say.nearby("%s smashed me, a nail! %s" % (ev.smasher, ev.smashed))
""",
    )
    hammer = await add_behaviored_thing(
        tw,
        "Hammer",
        """
@dataclass(frozen=True)
class Smashed(Event):
    smasher: Entity
    smashed: Entity

@language('start: "smash" noun', condition=Held())
async def smash(entity, smashing, person=None, say=None):
    if smashing is None:
        return fail("smash what now?")
    log.info("smash: %s", entity)
    await ctx.standard(Smashed, entity, smashing)
    return ok("you smashed a %s" % (smashing,))
""",
    )

    await tw.success("hold Hammer")
    await tw.failure("smash snail")
    await tw.success("smash nail")


@pytest.mark.asyncio
async def test_dynamic_maintains_scope(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await add_behaviored_thing(
        tw,
        "Nail",
        """
@dataclass(frozen=True)
class Smashed(Event):
    shmasher: Entity
    smashed: Entity

class Smashes(Scope):
    def __init__(self, smashes: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.smashes = smashes

    def increase(self):
        self.smashes += 1

@received(Smashed)
async def smashed(entity, hammer, say=None):
    with entity.make(Smashes) as smashes:
        smashes.increase()
        entity.touch()
        say.nearby("smashes: %d" % (smashes.smashes))
""",
    )
    hammer = await add_behaviored_thing(
        tw,
        "Hammer",
        """
@dataclass(frozen=True)
class Smashed(Event):
    smasher: Entity
    smashed: Entity

@language('start: "smash" noun', condition=Held())
async def smash(entity, smashing, person=None, say=None):
    if smashing is None:
        return fail("smash what now?")
    log.info("smash: %s", entity)
    await ctx.standard(Smashed, entity, smashing)
    return ok("you smashed a %s" % (smashing,))
""",
    )

    await tw.success("hold Hammer")
    await tw.success("smash nail")
    await tw.success("smash nail")
    await tw.success("smash nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        assert nail.chimeras["smashes"]["smashes"] == 3


@pytest.mark.asyncio
async def test_dynamic_receive_tick(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await add_behaviored_thing(
        tw,
        "Nail",
        """
class Rusting(Scope):
    def __init__(self, rust: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.rust = rust

    def increase(self):
        self.rust += 1

@received("tick")
async def rusting(entity, ev, say=None):
    with entity.make(Rusting) as rust:
        rust.increase()
        entity.touch()
        log.info("rusting")
        say.nearby("rust: %d" % (rust.rust))
""",
    )

    with tw.domain.session() as session:
        await session.tick(0)
        await session.save()

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        assert nail
        assert nail.chimeras["rusting"]["rust"] == 1


@pytest.mark.asyncio
async def test_dynamic_receive_drop_hook(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await add_behaviored_thing(
        tw,
        "Nail",
        """
class Rusting(Scope):
    def __init__(self, rust: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.rust = rust

    def increase(self):
        self.rust += 1

@received("ItemsDropped")
async def dropped(entity, ev, say=None):
    with entity.make(Rusting) as rust:
        rust.increase()
        entity.touch()
        log.info("dropped, rusting %d", rust.rust)
        say.nearby("rust: %d" % (rust.rust))
""",
    )

    await tw.success("hold Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        assert nail
        assert "rusting" not in nail.chimeras

    await tw.success("drop Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        assert nail
        assert nail.chimeras["rusting"]["rust"] == 1
