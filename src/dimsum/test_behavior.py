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
@pytest.mark.skip(reason="behavior refactor")
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
                "b:default",
                python="""
class Bank(Scope):
    def __init__(self, gold: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.gold = gold

@received("drop:after")
def dropped(entity, say=None, **kwargs):
    with entity.make(Bank) as bank:
        if bank.gold < 2:
            bank.gold += 1
            entity.touch()
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
@pytest.mark.skip(reason="behavior refactor")
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
                "b:test:wear:after",
                lua="""
function(s, world, area, player)
    player.invisible()
    debug(player.is_invisible())
end
""",
            )
            behave.add_behavior(
                world,
                "b:test:remove:after",
                lua="""
function(s, world, area, player)
    player.visible()
end
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
@pytest.mark.skip(reason="behavior refactor")
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
                "b:test:shake:after",
                lua="""
function(s, world, area, player)
    debug(area)
    return player.make_hands({
        name = "Flower Petal",
        color = "red",
    })
end
""",
            )

        await session.save()

    await tw.success("look")
    await tw.success("hold box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("shake box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2
        assert jacob.make(carryable.Containing).holding[1].creator == jacob

    await tw.success("look")


@pytest.mark.asyncio
@pytest.mark.skip(reason="behavior refactor")
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
                "b:test:shake:after",
                lua="""
function(s, world, area, player)
    debug(area)
    return area.make_here({
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
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

    await tw.success("shake box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1

        assert area.make(carryable.Containing).holding[0].creator.key == box.key
        assert (
            area.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 10
        )

    await tw.success("look")


@pytest.mark.asyncio
@pytest.mark.skip(reason="behavior refactor")
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
                "b:test:tick",
                lua="""
function(s, world, area, item)
    debug("ok", area, item, time)
    return area.make_here({
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
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


@pytest.mark.asyncio
@pytest.mark.skip(reason="behavior refactor")
async def test_behavior_create_kind(caplog):
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
                "b:test:tick",
                lua="""
function(s, world, area, item)
    return area.make_here({
        kind = item.kind("petals"),
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
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
        assert len(area.make(carryable.Containing).holding) == 2
        assert len(session.registrar.entities) == 5
        await session.tick(2)
        assert len(area.make(carryable.Containing).holding) == 2
        assert len(session.registrar.entities) == 5


@pytest.mark.asyncio
@pytest.mark.skip(reason="behavior refactor")
async def test_behavior_numbering_by_kind(caplog):
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
                "b:test:tick",
                lua="""
function(s, world, area, item)
    if area.number(item.kind("petals")) == 0 then
        return area.make_here({
            kind = item.kind("petals"),
            name = "Flower Petal",
            quantity = 10,
            color = "red",
        })
    else
        return area.make_here({
            kind = item.kind("leaves"),
            name = "Oak Leaves",
            quantity = 10,
            color = "red",
        })
    end
end
""",
            )

        await session.save()

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)

        await session.tick(0)
        assert len(area.make(carryable.Containing).holding) == 2

        await session.tick(1)
        assert len(area.make(carryable.Containing).holding) == 3


@pytest.mark.asyncio
@pytest.mark.skip(reason="behavior refactor")
async def test_behavior_numbering_person_by_name(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        w = await session.prepare()

        tree = tw.add_item_to_welcome_area(
            scopes.item(creator=w, props=properties.Common("A Lovely Tree")),
            session=session,
        )

        with tree.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                w,
                "b:test:tick",
                lua="""
function(s, world, area, item)
    if area.number("Jacob") == 0 then
        return area.make_here({
            kind = item.kind("leaves"),
            name = "Oak Leaves",
            quantity = 10,
            color = "red",
        })
    end
end
""",
            )

        await session.save()

    with tw.domain.session() as session:
        await session.tick(0)
        await session.save()

    with tw.domain.session() as session:
        w = await session.prepare()
        area = w.make(world.Welcoming).area
        assert len(area.make(carryable.Containing).holding) == 2

    with tw.domain.session() as session:
        await session.tick(1)
        await session.save()

    with tw.domain.session() as session:
        w = await session.prepare()
        area = w.make(world.Welcoming).area
        assert len(area.make(carryable.Containing).holding) == 2
