"""rsge-mcp: an MCP server for the rs.ge (Georgian Revenue Service) API."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rsge-mcp")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0.dev0"
