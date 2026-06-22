"""Opt-in live smoke tests. Skipped unless RSGE_RUN_INTEGRATION=1.

Hit the live rs.ge API with the documented public test account, read-only, honoring the
rate delay. Kept out of the default suite so CI never hammers the government endpoints.
Verified manually against production on 2026-06-22.
"""

from __future__ import annotations

import os

import pytest

from helpers import FakeMCP, make_ctx
from rsge_mcp.config import load_settings
from rsge_mcp.tools import common, taxpayer_public

pytestmark = pytest.mark.integration

_RUN = os.environ.get("RSGE_RUN_INTEGRATION") == "1"
_skip = pytest.mark.skipif(not _RUN, reason="set RSGE_RUN_INTEGRATION=1 to run live smoke tests")

# Documented public test individual that xdata returns data for. NOTE: the eAPI test id
# 206322102 returns a {Status:-100} error from xdata, so use this one for the public read.
_TEST_IDENT = "12345678910"


@_skip
@pytest.mark.asyncio
async def test_public_taxpayer_info_live() -> None:
    async with make_ctx(load_settings({"RSGE_ENV": "test"})) as ctx:
        cap = FakeMCP()
        taxpayer_public.register(cap, ctx)
        data = await cap.tools["rsge_taxpayer_public_info"](_TEST_IDENT)
        assert isinstance(data, list) and data
        assert data[0].get("FullName")


@_skip
@pytest.mark.asyncio
async def test_eapi_auth_and_read_live() -> None:
    # Public test creds (Tbilisi/123456) authenticate against eapi.rs.ge; GetUnits is a
    # simple authed read that exercises the full bearer-token flow end-to-end.
    async with make_ctx(load_settings({"RSGE_ENV": "test"})) as ctx:
        cap = FakeMCP()
        common.register(cap, ctx)
        units = await cap.tools["rsge_get_units"]()
        assert isinstance(units, list) and units
