"""A process-wide async gate enforcing a minimum delay between outbound calls.

CLAUDE.md mandates a courtesy delay against the live government endpoints. This gate
is shared by the REST and (Phase 2) SOAP clients. The clock and sleep functions are
injectable so tests can assert spacing without real waiting.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    def __init__(
        self,
        min_interval: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        # -inf so the first acquire never waits, regardless of the clock's base value.
        self._last = float("-inf")

    async def acquire(self) -> None:
        """Block until at least ``min_interval`` has elapsed since the last call."""
        async with self._lock:
            wait = self._min_interval - (self._clock() - self._last)
            if wait > 0:
                await self._sleep(wait)
            self._last = self._clock()
