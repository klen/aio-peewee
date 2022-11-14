"""Support Peewee ORM with asyncio."""

import typing as t
from collections import deque
from contextvars import ContextVar
from inspect import isawaitable

import peewee as pw
from playhouse import db_url, pool, cockroachdb as crdb
from playhouse.postgres_ext import PostgresqlExtDatabase
from playhouse.sqlite_ext import SqliteExtDatabase

from .transactions import _transaction_async, _atomic_async, _savepoint_async, _manual_async
from ._compat import aio_wait, aio_sleep, aio_event, FIRST_COMPLETED


__version__ = "0.4.1"

_ctx: t.Dict[str, ContextVar] = {
    'closed': ContextVar('closed', default=True),
    'conn': ContextVar('conn', default=None),
    'ctx': ContextVar('ctx', default=None),
    'transactions': ContextVar('transactions', default=None),
}


class _AsyncConnectionState(pw._ConnectionState):

    def __setattr__(self, name: str, value: t.Any):
        _ctx[name].set(value)

    def __getattr__(self, name: str) -> t.Any:
        return _ctx[name].get()


class DatabaseAsync:
    """Base interface for async databases."""

    if t.TYPE_CHECKING:
        connect: t.Callable

    def init(self, database: str, **kwargs):
        """Initialize the state."""
        self._state = _AsyncConnectionState()
        super(DatabaseAsync, self).init(database, **kwargs)  # type: ignore

    async def connect_async(self, reuse_if_open: bool = False) -> t.Any:
        """For purposes of compatability."""
        self.connect(reuse_if_open=reuse_if_open)
        return self._state.conn

    async def close_async(self):
        """Close the current connection."""
        if self.in_transaction():
            raise pw.OperationalError('Attempting to close database while transaction is open.')

        self.close()

    def transaction_async(self, *args, **kwargs):
        return _transaction_async(self, *args, **kwargs)

    def atomic_async(self, *args, **kwargs):
        return _atomic_async(self, *args, **kwargs)

    def savepoint_async(self, *args, **kwargs):
        return _savepoint_async(self, *args, **kwargs)

    def manual_async(self, *args, **kwargs):
        return _manual_async(self, *args, **kwargs)

    async def __aenter__(self):
        """Enter to async context."""
        conn = await self.connect_async(reuse_if_open=True)
        super().__enter__()
        return conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit from async context."""
        ctx = self._state.ctx.pop()
        try:
            ctx.__exit__(exc_type, exc_val, exc_tb)
        finally:
            if not self._state.ctx:
                await self.close_async()


class PooledDatabaseAsync(DatabaseAsync):
    """Base integface for async databases with connection pooling."""

    if t.TYPE_CHECKING:
        _in_use: t.List
        _max_connections: int
        _wait_timeout: float
        connect: t.Callable
        is_closed: t.Callable[..., bool]

    def init(self, database: str, **kwargs):
        """Prepare the limiter."""
        self._waiters: t.Deque = deque()
        super(PooledDatabaseAsync, self).init(database, **kwargs)

    async def connect_async(self, reuse_if_open: bool = False) -> t.Any:
        """Catch a connection asyncrounosly."""
        if reuse_if_open and not self.is_closed():
            return self._state.conn

        if len(self._in_use) >= self._max_connections:
            waiter = aio_event()
            self._waiters.append(waiter)
            try:
                await aio_wait(
                    waiter.wait(),
                    _raise_timeout(self._wait_timeout),
                    strategy=FIRST_COMPLETED,
                )

            except TimeoutError:
                raise pool.MaxConnectionsExceeded(
                    'Max connections exceeded, timed out attempting to connect.')

        self.connect(reuse_if_open=reuse_if_open)
        return self._state.conn

    async def _release(self):
        for _ in range(self._max_connections - len(self._in_use)):
            if not self._waiters:
                break
            waiter = self._waiters.popleft()
            coro = waiter.set()
            if coro and isawaitable(coro):
                await coro

    async def close_all_async(self):
        while self._waiters:
            super(PooledDatabaseAsync, self).close_all()
            await self._release()

    async def close_async(self):
        if self.in_transaction():
            raise pw.OperationalError('Attempting to close database while transaction is open.')
        super(PooledDatabaseAsync, self).close()
        await self._release()


class PostgresqlDatabaseAsync(DatabaseAsync, pw.PostgresqlDatabase):
    pass


class PostgresqlExtDatabaseAsync(DatabaseAsync, PostgresqlExtDatabase):
    pass


class PooledPostgresqlDatabaseAsync(PooledDatabaseAsync, pool.PooledPostgresqlDatabase):
    pass


class PooledPostgresqlExtDatabaseAsync(PooledDatabaseAsync, pool.PooledPostgresqlExtDatabase):
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
db_url.schemes['postgresext+async'] = db_url.schemes['postgresqlext+async'] = PostgresqlExtDatabaseAsync
db_url.schemes['postgres+pool+async'] = db_url.schemes['postgresql+pool+async'] = PooledPostgresqlDatabaseAsync  # noqa
db_url.schemes['postgresext+pool+async'] = db_url.schemes['postgresqlext+pool+async'] = PooledPostgresqlExtDatabaseAsync  # noqa
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
                await self.database.close_async()

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

# pylama: ignore=D,E501
