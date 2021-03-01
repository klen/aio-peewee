import typing as t
from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED
import sys
from inspect import iscoroutine
import asyncio

from sniffio import current_async_library

try:
    import trio

except ImportError:
    trio = None

# Python 3.8+
if sys.version_info >= (3, 8):
    create_task = asyncio.create_task

# Python 3.7
else:
    create_task = asyncio.ensure_future


try:
    import curio

except ImportError:
    curio = None


def aio_sleep(seconds: float = 0) -> t.Awaitable:
    """Return sleep coroutine."""
    if trio and current_async_library() == 'trio':
        return trio.sleep(seconds)

    if curio and current_async_library() == 'curio':
        return curio.sleep(seconds)

    return asyncio.sleep(seconds)


def aio_event():
    """Create async event."""
    if trio and current_async_library() == 'trio':
        return trio.Event()

    if curio and current_async_library() == 'curio':
        return curio.Event()

    return asyncio.Event()


async def aio_wait(*aws: t.Awaitable, strategy: str = ALL_COMPLETED) -> t.Any:
    """Run the coros concurently, wait for all completed or cancel others.

    Only ALL_COMPLETED, FIRST_COMPLETED are supported.
    """
    if not aws:
        return

    if trio and current_async_library() == 'trio':

        send_channel, receive_channel = trio.open_memory_channel(0)

        async with trio.open_nursery() as n:
            [n.start_soon(trio_jockey, aw, send_channel) for aw in aws]
            results = []
            for _ in aws:
                results.append(await receive_channel.receive())
                if strategy == FIRST_COMPLETED:
                    n.cancel_scope.cancel()
                    return results[0]

            return results

    if curio and current_async_library() == 'curio':
        wait = all if strategy == ALL_COMPLETED else any
        async with curio.TaskGroup(wait=wait) as g:
            [await g.spawn(aw) for aw in aws]

        return g.results if strategy == ALL_COMPLETED else g.result

    aws = tuple(create_task(aw) if iscoroutine(aw) else aw for aw in aws)
    done, pending = await asyncio.wait(aws, return_when=strategy)
    if strategy != ALL_COMPLETED:
        [task.cancel() for task in pending]
        await asyncio.gather(*pending, return_exceptions=True)
        return list(done)[0].result()

    return [t.result() for t in done]


async def trio_jockey(coro: t.Awaitable, channel):
    """Wait for the given coroutine and send result back to the given channel."""
    await channel.send(await coro)
