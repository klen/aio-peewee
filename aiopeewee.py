"""Support Peewee ORM with asyncio."""

import asyncio as aio
from contextvars import ContextVar
from collections import deque

import peewee as pw
from async_timeout import timeout
from playhouse import db_url, pool, cockroachdb as crdb
from playhouse.sqlite_ext import SqliteExtDatabase


version = "0.0.6"

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
        self._lock = pw._NoopLock()
        self._aiolock = aio.Lock()
        super(DatabaseAsync, self).init(database, **kwargs)

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
                await self.close_async()

    async def connect_async(self, reuse_if_open=False):
        """Get a connection."""
        if not reuse_if_open:
            self._state.reset()

        if self.is_closed():
            async with self._aiolock:
                self.connect()

        return self._state.conn

    async def close_async(self):
        """Close the current connection."""
        async with self._aiolock:
            return self.close()


class PooledDatabaseAsync(DatabaseAsync):
    """Base integface for async databases with connection pooling."""

    def init(self, database, **kwargs):
        """Prepare the pool."""
        self._waiters = deque()
        super(PooledDatabaseAsync, self).init(database, **kwargs)

    async def connect_async(self, reuse_if_open=False):
        """Catch a connection asyncrounosly."""
        if len(self._in_use) >= self._max_connections:
            fut = aio.Future()
            self._waiters.append(fut)
            try:
                async with timeout(self._wait_timeout):
                    await fut

            except aio.TimeoutError:
                self._waiters.remove(fut)
                raise pool.MaxConnectionsExceeded(
                    'Max connections exceeded, timed out attempting to connect.')

        return await super().connect_async(reuse_if_open=reuse_if_open)

    def _close(self, conn, close_conn=False):
        super(PooledDatabaseAsync, self)._close(conn, close_conn=close_conn)
        try:
            waiter = self._waiters.popleft()
            waiter.set_result(True)
        except IndexError:
            pass


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
db_url.schemes['sqliteexc+async'] = SqliteExtDatabaseAsync
db_url.schemes['sqliteexc+pool+async'] = PooledSqliteExtDatabaseAsync


class PeeweeASGIPlugin:
    """Support ASGI applications."""

    defaults = {
        'url': 'sqlite+async:///db.sqlite',
        'connection_params': {},
    }

    def __init__(self, **options):
        """Initialize the plugin."""
        self.config = dict(self.defaults, *options)
        self.models = {}
        self.database = db_url.connect(
            self.config['url'], **self.config['connection_params'])

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
                await self.database.close_async()

        return process

    def register(self, cls):
        """A decorator to register models with the plugin."""
        if issubclass(cls, pw.Model):
            self.models[cls._meta.table_name] = cls

        cls._meta.database = self.database

        return cls

    def conftest(self):
        """Integration with tests."""
        for model in self.models.values():
            try:
                model.create_table()
            except pw.OperationalError:
                pass

# pylama: ignore=D
