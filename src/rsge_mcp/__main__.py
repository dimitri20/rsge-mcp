"""Console entry point: ``python -m rsge_mcp`` / ``rsge-mcp`` (stdio transport)."""

from __future__ import annotations

import sys

from .errors import RsgeConfigError
from .server import build_server


def main() -> None:
    try:
        server = build_server()
    except RsgeConfigError as exc:
        # A concise line beats a traceback: MCP clients only show "server disconnected",
        # so the operator reads this from the client's stderr log.
        print(f"rsge-mcp: configuration error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    server.run()


if __name__ == "__main__":
    main()
