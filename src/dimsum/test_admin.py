import test

import model.scopes.users as users
import pytest


@pytest.mark.asyncio
async def test_auth_change():
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
async def test_auth_before():
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
