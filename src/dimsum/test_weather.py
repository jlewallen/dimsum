import pytest

from model import TickEvent
import library
import test


@pytest.mark.asyncio
async def test_area_weather_blows_small_items():
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()
        factory = library.example_world_factory(world)
        await factory(session)
        await session.save()

    await tw.add_jacob()

    assert await tw.success("go rocky")

    with tw.domain.session() as session:
        await session.prepare()
        await session.everywhere(TickEvent())

    await tw.close()
