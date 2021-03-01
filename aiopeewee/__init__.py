"""Support Peewee ORM with asyncio."""

import typing as t
from contextvars import ContextVar

import peewee as pw
from playhouse import db_url, pool, cockroachdb as crdb
from playhouse.sqlite_ext import SqliteExtDatabase
from ._compat import aio_semaphore, aio_wait, aio_sleep, FIRST_COMPLETED


try:
    import trio
except ImportError:
    trio = None


__version__ = "0.1.6"

_ctx = {
    'closed': ContextVar('closed', default=None),
    'conn': ContextVar('conn', default=None),
    'ctx': ContextVar('ctx', default=None),
    'transactions': ContextVar('transactions', default=None),
}


class _AsyncConnectionState(pw._ConnectionState):

    def __setattr__(self, name, value):
        _ctx[name].set(value)

    def __getattr__(self, name):
        return _ctx[name].get()


class DatabaseAsync:
    """Base interface for async databases."""

    def init(self, database, **kwargs):
        """Initialize the state."""
        self._state = _AsyncConnectionState()
        super(DatabaseAsync, self).init(database, **kwargs)

    async def connect_async(self, reuse_if_open=False):
        """For purposes of compatability."""
        self.connect(reuse_if_open=reuse_if_open)
        return self._state.conn

    async def __aenter__(self):
        """Enter to async context."""
        await self.connect_async(reuse_if_open=True)
        super().__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit from async context."""
        ctx = self._state.ctx.pop()
        try:
            ctx.__exit__(exc_type, exc_val, exc_tb)
        finally:
            if not self._state.ctx:
                self.close()


class PooledDatabaseAsync(DatabaseAsync):
    """Base integface for async databases with connection pooling."""

    def init(self, database, **kwargs):
        """Prepare the limiter."""
        self._limiter = None
        super(PooledDatabaseAsync, self).init(database, **kwargs)

    async def connect_async(self, reuse_if_open=False):
        """Catch a connection asyncrounosly."""
        if reuse_if_open and not self.is_closed():
            return self._state.conn

        if self._limiter is None:
            self._limiter = aio_semaphore(self._max_connections)
            self._limiter._value = max(0, self._max_connections - len(self._in_use))

        try:
            await aio_wait(
                self._limiter.acquire(),
                _raise_timeout(self._wait_timeout),
                strategy=FIRST_COMPLETED,
            )

        except TimeoutError:
            raise pool.MaxConnectionsExceeded(
                'Max connections exceeded, timed out attempting to connect.')

        self.connect(reuse_if_open=reuse_if_open)
        return self._state.conn

    def _connect(self):
        """Fix limiter for sync connections."""
        conn = super(PooledDatabaseAsync, self)._connect()
        if self._limiter:
            self._limiter._value = max(0, self._max_connections - len(self._in_use))

        return conn

    def _close(self, conn, close_conn=False):
        """Release the limiter."""
        super(PooledDatabaseAsync, self)._close(conn, close_conn=close_conn)
        if self._limiter and self._limiter._value < self._max_connections:
            self._limiter.release()


class PostgresqlDatabaseAsync(DatabaseAsync, pw.PostgresqlDatabase):
    pass


class PooledPostgresqlDatabaseAsync(PooledDatabaseAsync, pool.PooledPostgresqlDatabase):
    pass


class SqliteDatabaseAsync(DatabaseAsync, pw.SqliteDatabase):
    pass


class PooledSqliteDatabaseAsync(PooledDatabaseAsync, pool.PooledSqliteDatabase):
    pass


class SqliteExtDatabaseAsync(DatabaseAsync, SqliteExtDatabase):
    pass


class PooledSqliteExtDatabaseAsync(PooledDatabaseAsync, pool.PooledSqliteExtDatabase):
    pass


class MySQLDatabaseAsync(DatabaseAsync, pw.MySQLDatabase):
    pass


class PooledMySQLDatabaseAsync(PooledDatabaseAsync, pool.PooledMySQLDatabase):
    pass


class CockroachDatabaseAsync(DatabaseAsync, crdb.CockroachDatabase):
    pass


class PooledCockroachDatabaseAsync(PooledDatabaseAsync, crdb.PooledCockroachDatabase):
    pass


db_url.schemes['cockroachdb+async'] = db_url.schemes['crdb+async'] = CockroachDatabaseAsync
db_url.schemes['cockroachdb+pool+async'] = db_url.schemes['crdb+pool+async'] = PooledCockroachDatabaseAsync  # noqa
db_url.schemes['mysql+async'] = MySQLDatabaseAsync
db_url.schemes['mysql+pool+async'] = PooledMySQLDatabaseAsync
db_url.schemes['postgres+async'] = db_url.schemes['postgresql+async'] = PostgresqlDatabaseAsync
db_url.schemes['postgres+pool+async'] = db_url.schemes['postgresql+pool+async'] = PooledPostgresqlDatabaseAsync  # noqa
db_url.schemes['sqlite+async'] = SqliteDatabaseAsync
db_url.schemes['sqlite+pool+async'] = PooledSqliteDatabaseAsync
db_url.schemes['sqliteext+async'] = SqliteExtDatabaseAsync
db_url.schemes['sqliteext+pool+async'] = PooledSqliteExtDatabaseAsync


class PeeweeASGIPlugin:
    """Support ASGI applications."""

    defaults = {
        'url': 'sqlite+async:///db.sqlite',
        'connection_params': {},
    }

    def __init__(self, **options):
        """Initialize the plugin."""
        self.config = dict(self.defaults, **options)
        self.models = {}
        self.database = db_url.connect(
            self.config['url'], **self.config['connection_params'])

    def __getattr__(self, name):
        return getattr(self.database, name)

    async def shutdown(self):
        """Shutdown the database."""
        if hasattr(self.database, 'close_all'):
            self.database.close_all()

    def middleware(self, app):
        """Manage DB connections."""

        async def process(scope, receive, send):
            try:
                await self.database.connect_async()
                return await app(scope, receive, send)

            finally:
                self.database.close()

        return process

    def register(self, cls):
        """A decorator to register models with the plugin."""
        if issubclass(cls, pw.Model):
            self.models[cls._meta.table_name] = cls

        cls._meta.database = self.database

        return cls

    def create_tables(self, **options):
        """Create tables for the registered models."""
        for model in self.models.values():
            model.create_table(**options)


async def _raise_timeout(timeout: t.Union[int, float]):
    await aio_sleep(timeout)
    raise TimeoutError('Timeout occuirs.')

# pylama: ignore=D