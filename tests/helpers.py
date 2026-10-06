import asyncio
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


async def guard[T](coro: Awaitable[T], seconds: float = 5.0) -> T:
    return await asyncio.wait_for(coro, timeout=seconds)
