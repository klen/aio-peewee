"""Transactions with async interface."""

import peewee as pw


class _transaction_async(pw._transaction):

    async def __aenter__(self):
        """Enter to async context."""
        return super().__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit from async context."""
        return super().__exit__(exc_type, exc_val, exc_tb)


class _savepoint_async(pw._savepoint):

    async def __aenter__(self):
        """Enter to async context."""
        return super().__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit from async context."""
        return super().__exit__(exc_type, exc_val, exc_tb)


class _manual_async(pw._manual):

    async def __aenter__(self):
        """Enter to async context."""
        return super().__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit from async context."""
        return super().__exit__(exc_type, exc_val, exc_tb)


class _atomic_async(pw._atomic):

    async def __aenter__(self):
        """Enter to async context."""
        if self.db.transaction_depth() == 0:
            args, kwargs = self._transaction_args
            self._helper = self.db.transaction_async(*args, **kwargs)
        elif isinstance(self.db.top_transaction(), pw._manual):
            raise ValueError('Cannot enter atomic commit block while in manual commit mode.')
        else:
            self._helper = self.db.savepoint_async()
        return await self._helper.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit from async context."""
        await self._helper.__aexit__(exc_type, exc_val, exc_tb)
