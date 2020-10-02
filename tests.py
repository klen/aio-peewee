import asyncio as aio

import peewee as pw
import pytest


def test_setup():
    assert True


def test_package():
    from aiopeewee import version

    assert version


def test_connect():
    from aiopeewee import db_url
    from playhouse import cockroachdb as crdb

    db = db_url.connect('cockroachdb+async://')
    assert isinstance(db, crdb.CockroachDatabase)

    db = db_url.connect('crdb+async://')
    assert isinstance(db, crdb.CockroachDatabase)

    db = db_url.connect('cockroachdb+pool+async://')
    assert isinstance(db, crdb.CockroachDatabase)

    db = db_url.connect('crdb+pool+async://')
    assert isinstance(db, crdb.CockroachDatabase)

    db = db_url.connect('mysql+async://')
    assert isinstance(db, pw.MySQLDatabase)

    db = db_url.connect('mysql+pool+async://')
    assert isinstance(db, pw.MySQLDatabase)

    db = db_url.connect('postgres+async://')
    assert isinstance(db, pw.PostgresqlDatabase)

    db = db_url.connect('postgresql+async://')
    assert isinstance(db, pw.PostgresqlDatabase)

    db = db_url.connect('postgres+pool+async://')
    assert isinstance(db, pw.PostgresqlDatabase)

    db = db_url.connect('postgresql+pool+async://')
    assert isinstance(db, pw.PostgresqlDatabase)

    db = db_url.connect('sqlite+async://')
    assert isinstance(db, pw.SqliteDatabase)

    db = db_url.connect('sqlite+pool+async://')
    assert isinstance(db, pw.SqliteDatabase)


@pytest.mark.asyncio
async def test_basic():
    from aiopeewee import db_url, _AsyncConnectionState, SqliteDatabaseAsync

    db = db_url.connect('sqlite+async:///:memory:')
    assert db
    assert isinstance(db, SqliteDatabaseAsync)
    assert isinstance(db._state, _AsyncConnectionState)

    c1 = await db.connect_async()
    c2 = await db.connect_async()
    assert c1 is c2
    assert db._state.conn

    await db.close_async()
    assert not db._state.conn

    async with db:
        assert db._state.conn != c1


@pytest.mark.asyncio
async def test_pool():
    from aiopeewee import db_url, PooledSqliteDatabaseAsync, pool

    db = db_url.connect('sqlite+pool+async:///:memory:', max_connections=2, timeout=.1)
    assert db
    assert isinstance(db, PooledSqliteDatabaseAsync)

    c1 = await aio.create_task(db.connect_async())
    c2 = await aio.create_task(db.connect_async())
    assert c1 is not c2

    with pytest.raises(pool.MaxConnectionsExceeded):
        await db.connect_async()

    assert not len(db._waiters)

    db.close_all()
    c3 = await aio.create_task(db.connect_async())
    assert c3 is not c1
    assert c3 is not c2

    db.close_all()

    async def connect():
        await db.connect_async()
        await aio.sleep(.02)
        db.close()
        return True

    connects = await aio.gather(connect(), connect(), connect(), connect(), connect())
    assert all(connects)


@pytest.mark.asyncio
async def test_pw_task():
    pass


# TODO: transactions, context
