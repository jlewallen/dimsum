import logging
import pytest
from typing import Dict, List, Optional

from model import *
import scopes.behavior as behavior
import scopes as scopes
import test
from test_utils import *

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
async def wiggle(this, person, say):
    log.info("wiggle: %s", this)
    return "hey there!"

@language('start: "burp"')
async def burp(this, person, say):
    log.info("burp: %s", this)
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
async def wiggle(this, person, say):
    log.info("wiggle: %s", this)
    return "hey there!"
""",
    )

    await tw.failure("wiggle")
    await tw.success("hold Hammer")
    await tw.success("wiggle")


@pytest.mark.asyncio
async def test_dynamic_language_say_nearby(caplog):
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()

    hammer = await tw.add_behaviored_thing(
        tw,
        "Keys",
        """
@language('start: "jingle"', condition=Held())
async def jingle(this, person, say):
    log.info("jingle: %s", this)
    say.nearby("you hear kings jingling")
    return "hey there!"
""",
    )

    await tw.success("hold Keys")

    received: List[Renderable] = []

    async def handle_message(item: Renderable):
        received.append(item)

    assert tw.carla_key
    subscription = tw.domain.subscriptions.subscribe(tw.carla_key, handle_message)
    assert len(received) == 0

    await tw.success("jingle")
    assert len(received) == 1


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
        assert nail.scopes["smashes"]["smashes"] == 3


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
        assert nail.scopes["rusting"]["rust"] == 1


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
        assert "rusting" not in nail.scopes

    await tw.success("drop Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail.key)
        assert nail
        assert nail.scopes["rusting"]["rust"] == 1


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
async def test_exception_in_parse(silence_dynamic_errors, caplog):
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
            assert len(behave.get_default().logs) == 1


@pytest.mark.asyncio
async def test_exception_in_compile(silence_dynamic_errors, caplog):
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
async def test_exception_in_event_handler(silence_dynamic_errors, caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
@received(TickEvent)
def tick(this, ev, say):
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
async def test_exception_in_language_handler(silence_dynamic_errors, caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail = await tw.add_behaviored_thing(
        tw,
        "Nail",
        """
@language('start: "break"')
def break_nail(this, person, say):
    og.info("hello")
""",
    )

    reply = await tw.success("break")
    assert isinstance(reply, DynamicFailure)


@pytest.mark.asyncio
async def test_dynamic_inherited(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    jingles_base = await tw.add_behaviored_thing(
        tw,
        "base:jingles",
        """
@language('start: "jingle"', condition=Held())
async def jingle(this, person, say):
    log.info("jingle: %s", this)
    say.nearby("you hear kings jingling")
    return "hey there!"
""",
    )

    with tw.domain.session() as session:
        world = await session.prepare()
        keys = await tw.add_item_to_welcome_area(
            scopes.item(creator=world, parent=jingles_base, props=Common("Keys")),
            session=session,
        )
        await session.save()

    await tw.success("hold Keys")
    await tw.success("jingle")


@pytest.mark.asyncio
async def test_dynamic_hook_observed(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    door = await tw.add_behaviored_thing(tw, "Door", "")
    keys = await tw.add_behaviored_thing(
        tw,
        "Keys",
        """
@hooks.observed.hook
def hide_everything(resume, entity):
    log.info("hiding %s", entity)
    return []
""",
    )

    r = await tw.success("look")
    assert len(r.items) == 0

    await tw.success("hold Keys")
    await tw.success("obliterate")

    r = await tw.success("look")
    assert len(r.items) == 1


@pytest.mark.asyncio
async def test_dynamic_hook_never_hold(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    keys = await tw.add_behaviored_thing(
        tw,
        "Keys",
        """
@hooks.hold.hook
def never_hold(resume, person, entity):
    log.info("never-hold: %s", person)
    return False
""",
    )

    await tw.failure("hold Keys")


@pytest.mark.asyncio
async def test_dynamic_hook_never_enter(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north|south to Canada")

    await tw.success("go north")

    await tw.success("go south")

    really_heavy_keys = await tw.add_behaviored_thing(
        tw,
        "Really Heavy Keys",
        """
@hooks.enter.hook
def never_enter(resume, person, area):
    log.info("never-enter: %s", person)
    return False
""",
    )

    await tw.failure("go north")


@pytest.mark.asyncio
async def test_dynamic_hook_never_enter_when_held_hook_conditional(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north|south to Canada")

    await tw.success("go north")

    await tw.success("go south")

    really_heavy_keys = await tw.add_behaviored_thing(
        tw,
        "Really Heavy Keys",
        """
@hooks.enter.hook(condition=Held())
def never_enter(resume, person, area):
    log.info("never-enter: %s", person)
    return False
""",
    )

    await tw.success("go north")
    await tw.success("go south")
    await tw.success("hold keys")
    await tw.failure("go north")


@pytest.mark.asyncio
async def test_dynamic_received_say_nearby(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    hammer = await tw.add_behaviored_thing(
        tw,
        "Keys",
        """
@received(TickEvent)
async def make_noise(this, say):
    say.nearby("you hear an annoying buzzing sound")
    return ok()
""",
    )

    received: List[Renderable] = []

    async def handle_message(item: Renderable):
        received.append(item)

    assert tw.jacob_key
    subscription = tw.domain.subscriptions.subscribe(tw.jacob_key, handle_message)
    assert len(received) == 0

    with tw.domain.session() as session:
        await session.prepare()
        await session.tick(10)
        await session.save()

    assert len(received) == 1
