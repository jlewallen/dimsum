import pytest

import model.game as game
import model.properties as properties

import model.scopes.users as users

import test


@pytest.mark.asyncio
async def test_auth_change():
    tw = test.TestWorld()
    await tw.initialize()
    assert not tw.player.make(users.Auth).password
    await tw.execute("auth asdfasdf")
    assert tw.player.make(users.Auth).password


@pytest.mark.asyncio
async def test_auth_before():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("auth asdfasdf")
    assert tw.player.make(users.Auth).password
    auth_before = tw.player.make(users.Auth).password
    await tw.execute("auth foobarfoobar")
    auth_after = tw.player.make(users.Auth).password
    assert auth_before != auth_after
