import pytest

from loggers import get_logger
from model import *
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.mechanics as mechanics
import scopes as scopes
import test

# log = get_logger("dimsum.tests")


@pytest.mark.asyncio
async def test_drop_hammer_funny_gold(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        hammer = await tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=Common("Hammer")),
            session=session,
        )

        with hammer.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                None,
                python="""
class Bank(Scope):
    def __init__(self, gold: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.gold = gold

@received(ItemsDropped)
async def dropped(this, ev, say):
    with ev.source.make(Bank) as bank:
        if bank.gold < 2:
            bank.gold += 1
            ev.source.touch()
        log.info("gold=%d", bank.gold)
""",
            )

        await session.save()

    await tw.success("look")
    await tw.success("hold hammer")
    await tw.success("drop")
    await tw.success("hold hammer")
    await tw.success("drop")
    await tw.success("hold hammer")
    await tw.success("drop")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert jacob.scopes["bank"]["gold"] == 2


@pytest.mark.asyncio
async def test_wear_cape(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        cape = await tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=Common("Cape")), session=session
        )
        with cape.make(mechanics.Interactable) as inaction:
            inaction.link_activity("worn")

        with cape.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@received(ItemsWorn)
async def worn(this, ev, say):
    tools.hide(ev.source)

@received(ItemsUnworn)
async def unworn(this, ev, say):
    tools.show(ev.source)
""",
            )

        await session.save()

    await tw.success("look")
    await tw.success("hold cape")
    await tw.success("wear cape")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert jacob.make(mechanics.Visibility).is_invisible

    await tw.success("remove cape")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert not jacob.make(mechanics.Visibility).is_invisible

    await tw.success("drop")


@pytest.mark.asyncio
async def test_behavior_create_item(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        w = await session.prepare()

        box = await tw.add_item_to_welcome_area(
            scopes.item(creator=w, props=Common("A Colorful Box")),
            session=session,
        )
        with box.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                w,
                python="""
@language('start: "shake"')
async def shake(this, person, say, ctx):
    item = ctx.create_item(
        creator=person,
        props=Common("Flower Petal")
    )
    tools.hold(person, item)
    return "oh wow look at that!"
""",
            )

        await session.save()

    await tw.success("look")
    await tw.success("hold box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("shake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2
        assert jacob.make(carryable.Containing).holding[1].creator == jacob

    await tw.success("shake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 3
        assert jacob.make(carryable.Containing).holding[1].creator == jacob

    await tw.success("look")


@pytest.mark.asyncio
async def test_behavior_create_item_same_kind(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        w = await session.prepare()

        box = await tw.add_item_to_welcome_area(
            scopes.item(creator=w, props=Common("A Colorful Box")),
            session=session,
        )
        with box.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                w,
                python="""
@language('start: "shake"')
async def shake(this, person, say, ctx):
    item = ctx.create_item(
        creator=person,
        kind=this.get_kind("petal-1"),
        props=Common("Flower Petal"),
        initialize={ Carryable: dict(kind=this.get_kind("petal-1")) },
    )
    tools.hold(person, item)
    return "oh wow look at that!"
""",
            )

        await session.save()

    await tw.success("look")
    await tw.success("hold box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("shake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2
        assert jacob.make(carryable.Containing).holding[1].creator == jacob

    await tw.success("shake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2
        assert jacob.make(carryable.Containing).holding[1].creator == jacob

    await tw.success("look")


@pytest.mark.asyncio
async def test_behavior_create_quantified_item(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()
        box = await tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=Common("A Colorful Box")),
            session=session,
        )
        with box.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@language('start: "shake"')
async def shake(this, person, say, ctx):
    item = ctx.create_item(
        creator=person,
        props=Common("Flower Petal"),
        initialize={ Carryable: dict(quantity=10) }
    )
    tools.hold(tools.area_of(person), item)
    return "oh wow look at that!"
""",
            )

        await session.save()

    await tw.success("look")
    await tw.success("hold box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0

    await tw.success("shake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1
        assert jacob
        holding = area.make(carryable.Containing).holding
        assert holding and holding[0].creator
        assert holding[0].creator.key == jacob.key
        assert (
            area.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 10
        )

    await tw.success("look")


@pytest.mark.asyncio
async def test_behavior_time_passing(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        tree = await tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=Common("A Lovely Tree")),
            session=session,
        )
        with tree.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@received(TickEvent)
async def tick(this, ev, say, ctx):
    item = ctx.create_item(
        creator=this,
        props=Common("Flower Petal"),
        initialize={ Carryable: dict(quantity=10) }
    )
    tools.hold(tools.area_of(this), item)
""",
            )
        await session.save()

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)

        await session.everywhere(TickEvent())
        assert len(area.make(carryable.Containing).holding) == 2
        assert len(session.registrar.entities) == 6

        await session.everywhere(TickEvent())
        assert len(area.make(carryable.Containing).holding) == 3
        assert len(session.registrar.entities) == 7
