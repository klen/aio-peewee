import peewee as pw
import pytest
from anyio import create_task_group, sleep


@pytest.fixture(params=[
    pytest.param('asyncio'),
    pytest.param('trio'),
], autouse=True)
def anyio_backend(request):
    return request.param


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

    assert db_url.schemes['sqliteext+async']
    assert db_url.schemes['sqliteext+pool+async']


async def test_basic():
    from aiopeewee import db_url, _AsyncConnectionState, SqliteDatabaseAsync

    db = db_url.connect('sqlite+async:///:memory:')
    assert db
    assert isinstance(db, SqliteDatabaseAsync)
    assert isinstance(db._state, _AsyncConnectionState)

    c1 = await db.connect_async(True)
    c2 = await db.connect_async(True)
    assert c1 is c2
    assert db._state.conn

    db.close()
    assert not db._state.conn

    async with db:
        assert db._state.conn != c1


async def test_pool():
    from aiopeewee import db_url, PooledSqliteDatabaseAsync

    db = db_url.connect('sqlite+pool+async:///:memory:', max_connections=3, timeout=.1)
    assert db
    assert isinstance(db, PooledSqliteDatabaseAsync)
    assert db._limiter is None

    db.connect()
    c0 = db.connection()

    c1 = await db.connect_async(True)
    assert c1 is c0

    db.close_all()

    async def connect():
        conn = await db.connect_async()
        await sleep(.02)
        db.close()
        results.append(conn)

    results = []
    async with create_task_group() as tg:
        await tg.spawn(connect)
        await tg.spawn(connect)
        await tg.spawn(connect)
        await tg.spawn(connect)
        await tg.spawn(connect)

    assert all(results)
    assert len(set(results)) == 3
    assert db._limiter._value == 3


async def test_sqlite():
    from aiopeewee import db_url

    db = db_url.connect('sqlite+async:///:memory:')

    async def middleware():
        async with db:
            return db.execute_sql('select 42').fetchone()

    res, = await middleware()
    assert res == 42


# TODO: transactions, context
