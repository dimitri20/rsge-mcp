"""Session tools: sign out, and submit the SMS two-factor PIN."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_signout() -> str:
        """Sign out of the rs.ge eAPI session and invalidate the bearer token."""
        if ctx.session.has_token:
            await ctx.rest.post("/Users/SignOut", {})
        ctx.session.invalidate()
        return "Signed out."

    # Registered in EVERY 2FA mode: an account with SMS 2FA raises RsgePinRequiredError
    # even when RSGE_2FA_MODE is left at "off", and without this tool that state is a
    # dead end where each retried login fires another SMS. submit_pin works whenever a
    # PIN_TOKEN is pending, regardless of mode.
    @mcp.tool()
    async def rsge_submit_pin(pin: str) -> str:
        """Submit the SMS two-factor PIN to finish signing in to rs.ge.

        Use after a tool fails with a "PIN required" error: the SMS was already sent to
        the account's phone; do NOT retry the original tool first (each retry sends a
        new SMS) — submit the code here, then retry.
        """
        await ctx.session.submit_pin(pin)
        return "PIN accepted; session authenticated."
