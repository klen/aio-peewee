import asyncio as aio
from contextvars import ContextVar
from collections import deque

import peewee as pw
from async_timeout import timeout
from playhouse import db_url, pool, cockroachdb as crdb
from playhouse.sqlite_ext import SqliteExtDatabase


version = "0.0.1"

_ctx = {
    'closed': ContextVar('closed'),
    'conn': ContextVar('conn'),
    'ctx': ContextVar('ctx'),
    'transactions': ContextVar('transactions'),
}


class _AsyncConnectionState(pw._ConnectionState):

    def __setattr__(self, name, value):
        _ctx[name].set(value)

    def __getattr__(self, name):
        return _ctx[name].get()


class DatabaseAsync:

    def init(self, database, **kwargs):
        self._state = _AsyncConnectionState()
        self._lock = pw._NoopLock()
        self._aiolock = aio.Lock()
        super(DatabaseAsync, self).init(database, **kwargs)

    async def __aenter__(self):
        if self.is_closed():
            await self.connect_async()
        super().__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ctx = self._state.ctx.pop()
        try:
            ctx.__exit__(exc_type, exc_val, exc_tb)
        finally:
            if not self._state.ctx:
                await self.close_async()

    async def connect_async(self):
        """Catch a connection asyncrounosly."""
        if self.is_closed():
            async with self._aiolock:
                self.connect()
        return self._state.conn

    async def close_async(self):
        """Close the current connection asyncrounosly."""
        async with self._aiolock:
            return self.close()


class PooledDatabaseAsync(DatabaseAsync):

    def init(self, database, **kwargs):
        self._waiters = deque()
        super(PooledDatabaseAsync, self).init(database, **kwargs)

    async def connect_async(self):
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

        return await super().connect_async()

    def _close(self, *args, **kwargs):
        super(PooledDatabaseAsync, self)._close(*args, **kwargs)
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
