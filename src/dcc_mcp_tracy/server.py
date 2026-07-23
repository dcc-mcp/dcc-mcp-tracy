"""Standalone Tracy MCP server lifecycle."""

from __future__ import annotations

import os
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

from dcc_mcp_core import DccServerOptions
from dcc_mcp_core.server_base import DccServerBase

from .__version__ import __version__
from .runtime import TracyError, get_version

DEFAULT_PORT = 8766
_server: Optional["TracyMcpServer"] = None


class TracyMcpServer(DccServerBase):
    """Headless adapter backed by Tracy's official CLI utilities."""

    def __init__(self, port: int = DEFAULT_PORT) -> None:
        os.environ.setdefault("DCC_MCP_PYTHON_EXECUTABLE", sys.executable)
        options = DccServerOptions.from_env(
            "tracy",
            Path(__file__).resolve().parent / "skills",
            port=port,
            server_name="dcc-mcp-tracy",
            server_version=__version__,
        )
        super().__init__(options=options)

    def _version_string(self) -> str:
        try:
            return get_version()["version_output"]
        except TracyError:
            return "Tracy CLI unavailable"


def start_server(port: Optional[int] = None) -> TracyMcpServer:
    global _server
    if _server is None or not _server.is_running:
        selected_port = port or int(os.environ.get("DCC_MCP_TRACY_PORT", DEFAULT_PORT))
        _server = TracyMcpServer(selected_port)
        _server.register_builtin_actions()
        _server.start()
    return _server


def stop_server() -> None:
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def main() -> None:
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    start_server()
    try:
        stopped.wait()
    finally:
        stop_server()
