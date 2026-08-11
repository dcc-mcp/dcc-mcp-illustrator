"""Adobe Illustrator MCP adapter package."""

from .__version__ import __version__
from .server import IllustratorMcpServer, start_server, stop_server

__all__ = ["IllustratorMcpServer", "__version__", "start_server", "stop_server"]
