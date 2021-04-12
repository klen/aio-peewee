import peewee as pw
import pytest
from curio.task import ContextTask


@pytest.fixture(params=[
    'asyncio', 'trio',
    pytest.param(('curio', {'taskcls': ContextTask}), id='curio'),
], autouse=True)
def aiolib(request):
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

    assert db_url.schemes['postgresext+async']
    assert db_url.schemes['postgresext+pool+async'] 
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
    from aiopeewee._compat import aio_sleep, aio_wait

    db = db_url.connect('sqlite+pool+async:///:memory:', max_connections=3, timeout=.1)
    assert db
    assert isinstance(db, PooledSqliteDatabaseAsync)

    db.connect()
    c0 = db.connection()

    c1 = await db.connect_async(True)
    assert c1 is c0

    db.close_all()

    async def connect():
        conn = await db.connect_async()
        await aio_sleep(.02)
        await db.close_async()
        return conn

    results = await aio_wait(
        connect(),
        connect(),
        connect(),
        connect(),
        connect(),
    )

    assert all(results)
    assert len(set(results)) == 3
    assert not db._waiters


async def test_sqlite():
    from aiopeewee import db_url

    db = db_url.connect('sqlite+async:///:memory:')

    async def middleware():
        async with db:
            return db.execute_sql('select 42').fetchone()

    res, = await middleware()
    assert res == 42


async def test_asgi():
    from aiopeewee import PeeweeASGIPlugin
    from asgi_tools import App
    from asgi_tools.tests import ASGITestClient

    app = App(debug=True)
    client = ASGITestClient(app)
    db = PeeweeASGIPlugin(url='sqlite+async:///:memory:')
    app.middleware(db.middleware)

    @app.route('/')
    async def sql(request):
        result, = db.execute_sql(f"select { request.url.query['num'] }").fetchone()
        return result

    res = await client.get('/', query={'num': 42})
    assert res.status_code == 200
    assert await res.json() == 42


# TODO: transactions, context
