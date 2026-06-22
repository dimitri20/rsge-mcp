"""Tests for the rate limiter."""

from __future__ import annotations

import pytest

from rsge_mcp.rest.rate_limit import RateLimiter

pytestmark = pytest.mark.unit


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.mark.asyncio
async def test_first_call_does_not_wait() -> None:
    clock = FakeClock()
    slept: list[float] = []

    async def fake_sleep(d: float) -> None:
        slept.append(d)
        clock.t += d

    limiter = RateLimiter(0.3, clock=clock, sleep=fake_sleep)
    await limiter.acquire()
    assert slept == []


@pytest.mark.asyncio
async def test_second_immediate_call_waits_the_interval() -> None:
    clock = FakeClock()
    slept: list[float] = []

    async def fake_sleep(d: float) -> None:
        slept.append(d)
        clock.t += d

    limiter = RateLimiter(0.3, clock=clock, sleep=fake_sleep)
    await limiter.acquire()  # t=0, no wait
    await limiter.acquire()  # immediate -> must wait ~0.3
    assert slept and abs(slept[0] - 0.3) < 1e-9


@pytest.mark.asyncio
async def test_no_wait_when_interval_already_elapsed() -> None:
    clock = FakeClock()
    slept: list[float] = []

    async def fake_sleep(d: float) -> None:
        slept.append(d)
        clock.t += d

    limiter = RateLimiter(0.3, clock=clock, sleep=fake_sleep)
    await limiter.acquire()
    clock.t += 1.0  # plenty of time passes
    await limiter.acquire()
    assert slept == []
