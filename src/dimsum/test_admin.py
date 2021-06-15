import pytest

import game
import properties
import test


@pytest.mark.asyncio
async def test_auth_change():
    tw = test.TestWorld()
    await tw.initialize()
    assert properties.Password not in tw.player.props
    await tw.execute("auth asdfasdf")
    assert properties.Password in tw.player.props
    assert tw.player.props[properties.Password] != None


@pytest.mark.asyncio
async def test_auth_before():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("auth asdfasdf")
    assert tw.player.props[properties.Password] != None
    auth_before = tw.player.props[properties.Password]
    await tw.execute("auth foobarfoobar")
    auth_after = tw.player.props[properties.Password]
    assert auth_before != auth_after
