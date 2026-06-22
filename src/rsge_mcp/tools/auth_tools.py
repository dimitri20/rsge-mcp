"""Session tools: sign out, and (in 2FA tool mode) submit the SMS PIN."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import TwoFactorMode

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

    # Only expose the PIN tool when 2FA is handled interactively.
    if ctx.settings.two_factor_mode is TwoFactorMode.TOOL:

        @mcp.tool()
        async def rsge_submit_pin(pin: str) -> str:
            """Submit the SMS two-factor PIN to finish signing in to rs.ge."""
            await ctx.session.submit_pin(pin)
            return "PIN accepted; session authenticated."
