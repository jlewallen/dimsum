import sys
import logging
import pytest

import model.game as game
import model.properties as properties
import model.world as world

import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable
import model.scopes.behavior as behavior
import model.scopes as scopes

import plugins.default.actions

import test

log = logging.getLogger("dimsum.tests")


@pytest.mark.asyncio
async def test_drop_hammer_funny_gold(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        hammer = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("Hammer")),
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
async def dropped(entity, ev=None, say=None, **kwargs):
    with ev.living.make(Bank) as bank:
        if bank.gold < 2:
            bank.gold += 1
            ev.living.touch()
        log.info("gold=%d kwargs=%s", bank.gold, kwargs)
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
        assert jacob.chimeras["bank"]["gold"] == 2


@pytest.mark.asyncio
async def test_wear_cape(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        cape = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("Cape")), session=session
        )
        with cape.make(mechanics.Interactable) as inaction:
            inaction.link_activity("worn")

        with cape.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@received(ItemsWorn)
async def worn(entity, ev=None, say=None, **kwargs):
    tools.hide(ev.living)

@received(ItemsUnworn)
async def unworn(entity, ev=None, say=None, **kwargs):
    tools.show(ev.living)
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

        box = tw.add_item_to_welcome_area(
            scopes.item(creator=w, props=properties.Common("A Colorful Box")),
            session=session,
        )
        with box.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                w,
                python="""
@language('start: "shake"')
async def shake(entity, person=None, say=None):
    item = ctx.create_item(creator=person, props=properties.Common("Flower Petal"))
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

    await tw.success("look")


@pytest.mark.asyncio
async def test_behavior_create_quantified_item(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()
        box = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("A Colorful Box")),
            session=session,
        )
        with box.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@language('start: "shake"')
async def shake(entity, person=None, say=None):
    item = ctx.create_item(
        creator=person,
        props=properties.Common("Flower Petal"),
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
        area = world.find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0

    await tw.success("shake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1

        assert area.make(carryable.Containing).holding[0].creator.key == jacob.key
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

        tree = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("A Lovely Tree")),
            session=session,
        )
        with tree.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
@received(TickEvent)
async def tick(entity, ev, say=None):
    item = ctx.create_item(
        creator=entity,
        props=properties.Common("Flower Petal"),
        initialize={ Carryable: dict(quantity=10) }
    )
    tools.hold(tools.area_of(entity), item)
""",
            )
        await session.save()

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)

        await session.tick(0)
        assert len(area.make(carryable.Containing).holding) == 2
        assert len(session.registrar.entities) == 5

        await session.tick(1)
        assert len(area.make(carryable.Containing).holding) == 3
        assert len(session.registrar.entities) == 6
