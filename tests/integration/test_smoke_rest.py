"""Opt-in live smoke test. Skipped unless RSGE_RUN_INTEGRATION=1.

Hits the live rs.ge API with the public test account, read-only, honoring the rate
delay. Kept out of the default suite so CI never hammers the government endpoints.
"""

from __future__ import annotations

import os

import pytest

from rsge_mcp.config import load_settings
from rsge_mcp.context import build_context

pytestmark = pytest.mark.integration

_RUN = os.environ.get("RSGE_RUN_INTEGRATION") == "1"
_TEST_IDENT = "206322102"  # documented public test taxpayer id


@pytest.mark.skipif(not _RUN, reason="set RSGE_RUN_INTEGRATION=1 to run live smoke tests")
@pytest.mark.asyncio
async def test_taxpayer_public_info_live() -> None:
    settings = load_settings({"RSGE_ENV": "test"})
    ctx = build_context(settings)
    try:
        data = await ctx.rest.post(
            "/TaxPayer/RSPublicInfo",
            {"IdentCode": _TEST_IDENT},
            auth=False,
            base=settings.hosts.xdata_base,
        )
        assert data is not None
    finally:
        await ctx.http.aclose()
