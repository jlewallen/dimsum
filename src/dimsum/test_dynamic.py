import logging
import test
from typing import Dict, List, Optional

import model.game as game
import model.properties as properties
import model.scopes as scopes
import model.scopes.behavior as behavior
import pytest

log = logging.getLogger("dimsum.tests")


@pytest.mark.asyncio
async def test_multiple_simple_verbs(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.failure("wiggle")

    hammer = await tw.add_behaviored_thing(
        tw,
        "Hammer",
        """
@language('start: "wiggle"')
async def wiggle(entity, person, say):
    log.info("wiggle: %s", entity)
    return "hey there!"

@language('start: "burp"')
async def burp(entity, person, say):
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

    hammer = await tw.add_behaviored_thing(
        tw,
        "Hammer",
        """
@language('start: "wiggle"', condition=Held())
async def wiggle(entity, person, say):
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

    hammer = await tw.add_behaviored_thing(
        tw,
        "Keys",
        """
@language('start: "jingle"', condition=Held())
async def jingle(entity, person, say):
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

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
@dataclass(frozen=True)
class Smashed(Event):
    smasher: Entity
    smashed: Entity

@received(Smashed)
async def smashed(this: Entity, ev: Smashed, say):
    log.info("smashed! %s", ev)
    say.nearby("%s smashed me, a nail! %s" % (ev.smasher, ev.smashed))
""",
    )
    hammer = await tw.add_behaviored_thing(
        tw,
        "Hammer",
        """
@dataclass(frozen=True)
class Smashed(Event):
    smasher: Entity
    smashed: Entity

@language('start: "smash" noun', condition=Held())
async def smash(this, smashing, person, say):
    if smashing is None:
        return fail("smash what now?")
    log.info("smash: %s", this)
    await ctx.standard(Smashed, this, smashing)
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

    nail = await tw.add_behaviored_thing(
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
async def smashed(this, ev, say):
    with this.make(Smashes) as smashes:
        smashes.increase()
        this.touch()
        say.nearby("smashes: %d" % (smashes.smashes))
""",
    )
    hammer = await tw.add_behaviored_thing(
        tw,
        "Hammer",
        """
@dataclass(frozen=True)
class Smashed(Event):
    smasher: Entity
    smashed: Entity

@language('start: "smash" noun', condition=Held())
async def smash(this, smashing, person, say):
    if smashing is None:
        return fail("smash what now?")
    log.info("smash: %s", this)
    await ctx.standard(Smashed, this, smashing)
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

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
class Rusting(Scope):
    def __init__(self, rust: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.rust = rust

    def increase(self):
        self.rust += 1

@received(TickEvent)
async def rusting(this, ev, say):
    with this.make(Rusting) as rust:
        rust.increase()
        this.touch()
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

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
class Rusting(Scope):
    def __init__(self, rust: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.rust = rust

    def increase(self):
        self.rust += 1

@received(ItemsDropped)
async def dropped(this, ev, say):
    with this.make(Rusting) as rust:
        rust.increase()
        this.touch()
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


@pytest.mark.asyncio
async def test_no_evaluators_understands_nothing(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
evaluators = []
""",
    )

    await tw.failure("hold Nail")


@pytest.mark.asyncio
async def test_exception_in_parse(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
asdf;
""",
    )

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 0

    await tw.success("hold Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 2


@pytest.mark.asyncio
async def test_exception_in_compile(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
og.info("hello")
""",
    )

    await tw.success("hold Nail")


@pytest.mark.asyncio
async def test_exception_in_event_handler(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
@received(TickEvent)
def tick(this, ev, say=None):
    og.info("hello")
""",
    )

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 0

    with tw.domain.session() as session:
        await session.prepare()
        await session.tick(10)
        await session.save()

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 1


@pytest.mark.asyncio
async def test_exception_in_language_handler(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
@language('start: "break"')
def break_nail(this, person=None, say=None):
    og.info("hello")
""",
    )

    reply = await tw.success("break")
    assert isinstance(reply, game.DynamicFailure)
