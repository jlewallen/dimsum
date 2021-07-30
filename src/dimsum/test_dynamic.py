import time
import pytest
import freezegun
from datetime import datetime
from typing import Dict, List, Optional

import domains
from model import *
from scheduling import Scheduler
from loggers import get_logger
from dynamic import DynamicFailure
from scheduling import WhenCron
import scopes.behavior as behavior
import scopes as scopes
import test
from test_utils import *


@pytest.mark.asyncio
async def test_multiple_simple_verbs(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.failure("wiggle")

    hammer_key = await tw.add_behaviored_thing(
        "Hammer",
        """
@ds.language('start: "wiggle"')
async def wiggle(this, person, say):
    log.info("wiggle: %s", this)
    return "hey there!"

@ds.language('start: "burp"')
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

    hammer_key = await tw.add_behaviored_thing(
        "Hammer",
        """
@ds.language('start: "wiggle"', condition=Held())
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

    hammer_key = await tw.add_behaviored_thing(
        "Keys",
        """
@ds.language('start: "jingle"', condition=Held())
async def jingle(this, person, say):
    log.info("jingle: %s", this)
    say.nearby(this, "you hear kings jingling")
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

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
@dataclass(frozen=True)
class Smashed(StandardEvent):
    smasher: Entity
    smashed: Entity

@ds.received(Smashed)
async def smashed(this: Entity, ev: Smashed, say):
    log.info("smashed! %s", ev)
    say.nearby(this, "%s smashed me, a nail! %s" % (ev.smasher, ev.smashed))
""",
    )
    hammer_key = await tw.add_behaviored_thing(
        "Hammer",
        """
@dataclass(frozen=True)
class Smashed(StandardEvent):
    smasher: Entity
    smashed: Entity

@ds.language('start: "smash" noun', condition=Held())
async def smash(this, smashing, person, say, ctx):
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

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
@dataclass(frozen=True)
class Smashed(StandardEvent):
    shmasher: Entity
    smashed: Entity

class Smashes(Scope):
    def __init__(self, smashes: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.smashes = smashes

    def increase(self):
        self.smashes += 1

@ds.received(Smashed)
async def smashed(this, ev, say):
    with this.make(Smashes) as smashes:
        smashes.increase()
        this.touch()
        say.nearby(this, "smashes: %d" % (smashes.smashes))
""",
    )
    hammer_key = await tw.add_behaviored_thing(
        "Hammer",
        """
@dataclass(frozen=True)
class Smashed(StandardEvent):
    smasher: Entity
    smashed: Entity

@ds.language('start: "smash" noun', condition=Held())
async def smash(this, smashing, person, say, ctx):
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
        nail = await session.materialize(key=nail_key)
        assert nail.scopes["smashes"]["smashes"] == 3


@pytest.mark.asyncio
async def test_dynamic_receive_tick(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
class Rusting(Scope):
    def __init__(self, rust: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.rust = rust

    def increase(self):
        self.rust += 1

@ds.received(TickEvent)
async def rusting(this, ev, say):
    with this.make(Rusting) as rust:
        rust.increase()
        this.touch()
        log.info("rusting")
        say.nearby(this, "rust: %d" % (rust.rust))
""",
    )

    with tw.domain.session() as session:
        await session.prepare()
        await session.everywhere(TickEvent())
        await session.save()

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        assert nail
        assert nail.scopes["rusting"]["rust"] == 1


@pytest.mark.asyncio
async def test_dynamic_receive_drop_hook(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
class Rusting(Scope):
    def __init__(self, rust: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.rust = rust

    def increase(self):
        self.rust += 1

@ds.received(ItemsDropped)
async def dropped(this, ev, say):
    with this.make(Rusting) as rust:
        rust.increase()
        this.touch()
        log.info("dropped, rusting %d", rust.rust)
        say.nearby(this, "rust: %d" % (rust.rust))
""",
    )

    await tw.success("hold Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        assert nail
        assert "rusting" not in nail.scopes

    await tw.success("drop Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        assert nail
        assert nail.scopes["rusting"]["rust"] == 1


@pytest.mark.asyncio
async def test_no_evaluators_understands_nothing(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
ds.evaluators([])
""",
    )

    await tw.failure("hold Nail")


@pytest.mark.asyncio
async def test_exception_in_parse(silence_dynamic_errors, caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
asdf;
""",
    )

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 0

    with pytest.raises(NameError):
        await tw.success("hold Nail")

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 2


@pytest.mark.asyncio
async def test_exception_in_compile(silence_dynamic_errors, caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
og.info("hello")
""",
    )

    with pytest.raises(NameError):
        await tw.success("hold Nail")


@pytest.mark.asyncio
async def test_exception_in_event_handler(silence_dynamic_errors, caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
@ds.received(TickEvent)
def tick(this, ev, say):
    og.info("hello")
""",
    )

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 0

    with pytest.raises(NameError):
        with tw.domain.session() as session:
            await session.prepare()
            await session.everywhere(TickEvent())
            await session.save()

    with tw.domain.session() as session:
        nail = await session.materialize(key=nail_key)
        with nail.make(behavior.Behaviors) as behave:
            assert len(behave.get_default().logs) == 1


@pytest.mark.asyncio
async def test_exception_in_language_handler(silence_dynamic_errors, caplog):
    tw = test.TestWorld()
    await tw.initialize()

    nail_key = await tw.add_behaviored_thing(
        "Nail",
        """
@ds.language('start: "break"')
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

    jingles_base_key = await tw.add_behaviored_thing(
        "base:jingles",
        """
@ds.language('start: "jingle"', condition=Held())
async def jingle(this, person, say):
    log.info("jingle: %s", this)
    say.nearby(this, "you hear kings jingling")
    return "hey there!"
""",
    )

    with tw.domain.session() as session:
        world = await session.prepare()
        jingles_base = await session.materialize(key=jingles_base_key)
        assert jingles_base
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

    await tw.add_behaviored_thing("Door", "")
    await tw.add_behaviored_thing(
        "Keys",
        """
@ds.hooks.observed.hook
async def hide_everything(resume, entity):
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

    await tw.add_behaviored_thing(
        "Keys",
        """
@ds.hooks.hold.hook
async def never_hold(resume, person, entity):
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

    await tw.add_behaviored_thing(
        "Really Heavy Keys",
        """
@ds.hooks.enter.hook
async def never_enter(resume, person, area):
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

    await tw.add_behaviored_thing(
        "Really Heavy Keys",
        """
@ds.hooks.enter.hook(condition=Held())
async def never_enter(resume, person, area, this):
    log.info("never-enter: %s keys=%s", person, this)
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

    await tw.add_behaviored_thing(
        "Keys",
        """
@ds.received(TickEvent)
async def make_noise(this, say):
    say.nearby(this, "you hear an annoying buzzing sound")
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
        await session.everywhere(TickEvent())
        await session.save()

    assert len(received) == 1


@pytest.mark.asyncio
async def test_dynamic_cron_5_minutes(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.add_behaviored_thing(
        "Keys",
        """
@ds.cron("*/5 * * * *")
async def make_noise(this, say):
    say.nearby(this, "you hear an annoying buzzing sound")
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
        scheduler = Scheduler(session)
        await scheduler.service(datetime.now())
        await session.save()

    with freezegun.freeze_time() as frozen_datetime:
        with tw.domain.session() as session:
            await session.prepare()
            scheduler = Scheduler(session)
            future = await scheduler.peek(datetime.max)
            assert future
            frozen_datetime.move_to(future[0].when)
            await scheduler.service(datetime.now())
            await session.save()

    assert len(received) == 1


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_dynamic_cron_5_minutes_and_3_minutes(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.add_behaviored_thing(
        "Keys",
        """
@ds.cron("*/5 * * * *")
async def every_5(this, say):
    say.nearby(this, "every 5")
    return ok()

@ds.cron("*/3 * * * *")
async def every_3(this, say):
    say.nearby(this, "every 3")
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
        scheduler = Scheduler(session)
        await scheduler.service(datetime.now())
        await session.save()

    assert len(received) == 0

    # assert isinstance(tw.domain.scheduled, WhenCron)
    # assert tw.domain.scheduled.crons[0].spec == "*/3 * * * *"

    with freezegun.freeze_time() as frozen_datetime:
        with tw.domain.session() as session:
            await session.prepare()
            scheduler = Scheduler(session)
            future = await scheduler.peek(datetime.max)
            assert future
            frozen_datetime.move_to(future[0].when)
            await scheduler.service(datetime.now())
            await session.save()

    assert len(received) == 1

    # assert tw.domain.scheduled
    # assert isinstance(tw.domain.scheduled, WhenCron)
    # assert tw.domain.scheduled.crons[0].spec == "*/5 * * * *"

    with freezegun.freeze_time() as frozen_datetime:
        with tw.domain.session() as session:
            await session.prepare()
            scheduler = Scheduler(session)
            future = await scheduler.peek(datetime.max)
            assert future
            frozen_datetime.move_to(future[0].when)
            await scheduler.service(datetime.now())
            await session.save()

    assert len(received) == 2

    # assert tw.domain.scheduled
    # assert isinstance(tw.domain.scheduled, WhenCron)
    # assert tw.domain.scheduled.crons[0].spec == "*/3 * * * *"
