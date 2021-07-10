import logging
import pytest
from typing import Optional, List

import domains
from model import *
import scopes.ownership as ownership


log = logging.getLogger("dimsum")


class SimpleCore(Scope):
    def __init__(self, name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name


class SimpleHolding(Scope):
    def __init__(self, holding=None, **kwargs):
        super().__init__(**kwargs)
        self.holding = holding if holding else []

    def add_item(self, entity: Entity):
        self.holding.append(entity)


class Remembering(Scope):
    def __init__(self, entities: Optional[List[Entity]] = None, **kwargs):
        super().__init__(**kwargs)
        self.entities = entities if entities else []


def remember(world: World, e: Entity):
    with world.make(Remembering) as remembering:
        remembering.entities.append(e)
        world.touch()


@pytest.mark.asyncio
async def test_chimeric_entities_serialize(caplog):
    domain = domains.Domain()

    with domain.session() as session:
        universe = await session.prepare()

        jacob = Entity(
            creator=universe, props=Common(name="Jacob"), scopes=[SimpleCore]
        )
        session.register(jacob)
        remember(universe, jacob)

        toy = Entity(creator=universe, props=Common(name="Toy"), scopes=[SimpleCore])
        session.register(toy)
        remember(universe, toy)

        with jacob.make(SimpleHolding) as holding:
            with jacob.make(SimpleCore) as core:
                pass
            holding.add_item(toy)

        await session.save()

    after = await domain.reload()

    assert await after.store.number_of_entities() == 3


def make_person(
    props: Optional[Common] = None, creator: Optional[Entity] = None, **kwargs
):
    person = Entity(props=props, creator=creator, scopes=[SimpleCore], **kwargs)

    assert props

    with person.make(SimpleCore) as core:
        core.name = props.name

    with person.make(SimpleHolding) as holding:
        pass

    return person


def make_thing(
    props: Optional[Common] = None, creator: Optional[Entity] = None, **kwargs
):
    thing = Entity(props=props, creator=creator, scopes=[ownership.Ownership], **kwargs)

    assert props

    with thing.make(ownership.Ownership) as change:
        change.owner = creator

    with thing.make(SimpleCore) as core:
        core.name = props.name

    with thing.make(SimpleHolding) as holding:
        pass

    return thing


@pytest.mark.asyncio
async def test_specialization_classes(caplog):
    domain = domains.Domain()

    with domain.session() as session:
        universe = await session.prepare()

        person = make_person(creator=universe, props=Common(name="Jacob"))
        session.register(person)
        remember(universe, person)

        toy = make_thing(creator=universe, props=Common(name="Toy"))
        session.register(toy)
        remember(universe, toy)

        await session.save()

    after = await domain.reload()

    assert await after.store.number_of_entities() == 3
