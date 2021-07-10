import pytest

import scopes.users as users
import test


@pytest.mark.asyncio
async def test_admin_auth_change():
    tw = test.TestWorld()
    await tw.initialize()
    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert not jacob.make(users.Auth).password

    await tw.execute("auth asdfasdf")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert jacob.make(users.Auth).password


@pytest.mark.asyncio
async def test_admin_auth_before():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("auth asdfasdf")

    auth_before = None
    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert jacob.make(users.Auth).password
        auth_before = jacob.make(users.Auth).password

    await tw.execute("auth foobarfoobar")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        auth_after = jacob.make(users.Auth).password
        assert auth_before != auth_after


@pytest.mark.asyncio
async def test_admin_invite():
    tw = test.TestWorld()
    await tw.initialize()

    r = await tw.execute("invite foobar")
    assert r.kwargs
