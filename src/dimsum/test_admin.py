import pytest

import game
import test


@pytest.mark.asyncio
async def test_auth_change():
    tw = test.TestWorld()
    await tw.initialize()
    assert "s:password" not in tw.player.props
    await tw.execute("auth asdfasdf")
    assert "s:password" in tw.player.props
    assert tw.player.props["s:password"] != None


@pytest.mark.asyncio
async def test_auth_before():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("auth asdfasdf")
    assert tw.player.props["s:password"] != None
    auth_before = tw.player.props["s:password"]
    await tw.execute("auth foobarfoobar")
    auth_after = tw.player.props["s:password"]
    assert auth_before != auth_after
