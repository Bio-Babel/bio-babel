"""Stdio JSON-RPC 2.0 transport, MCP-compatible at the wire level.

We deliberately avoid hard-binding to a specific MCP SDK so that:

  * Smoke tests can drive the server without external deps.
  * Users can wire any MCP client (Claude Code, Cursor, Continue, ...) that
    speaks the standard `initialize`/`tools/list`/`tools/call` protocol.

All biobabel tools are read-only and return a single result envelope, so the
transport has no streaming / progress-notification path.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from biobabel import __version__
from biobabel.mcp.server import BiobabelMCPServer

PROTOCOL_VERSION = "2024-11-05"


class StdioTransport:
    def __init__(
        self,
        server: BiobabelMCPServer,
        *,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        self.server = server
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout

    def serve_forever(self) -> None:
        for line in self._stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                self._send(_jsonrpc_error(None, -32700, f"parse error: {exc}"))
                continue
            self._handle(req)

    def _handle(self, req: dict[str, Any]) -> None:
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
            self._send(_jsonrpc_error(None, -32600, "invalid request"))
            return
        method = req.get("method", "")
        msg_id = req.get("id")
        params = req.get("params") or {}

        if method == "initialize":
            self._send(
                _jsonrpc_result(
                    msg_id,
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "serverInfo": {"name": "biobabel", "version": __version__},
                        "capabilities": {"tools": {"listChanged": False}},
                    },
                )
            )
        elif method == "notifications/initialized":
            return  # no response for notifications
        elif method == "tools/list":
            tools = [
                {
                    "name": name,
                    "description": self.server.tool(name).description,
                    "inputSchema": self.server.tool(name).input_schema,
                }
                for name in self.server.tool_names
            ]
            self._send(_jsonrpc_result(msg_id, {"tools": tools}))
        elif method == "tools/call":
            self._handle_tools_call(msg_id, params)
        else:
            self._send(_jsonrpc_error(msg_id, -32601, f"method not found: {method}"))

    def _handle_tools_call(self, msg_id: Any, params: dict[str, Any]) -> None:
        name = params.get("name", "")
        args = params.get("arguments") or {}

        try:
            envelope = self.server.call(name, **args)
        except Exception as exc:  # noqa: BLE001 — last-resort guard so a buggy
            # handler can't kill the stdio loop; the raised exception is
            # surfaced to the LLM as a structured error envelope with the
            # full type+message rather than swallowed silently.
            envelope = {
                "ok": False,
                "tool_name": name,
                "error_code": "exception",
                "message": f"{type(exc).__name__}: {exc}",
            }
        self._send(
            _jsonrpc_result(
                msg_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps(envelope, ensure_ascii=False)}
                    ],
                    "isError": not envelope.get("ok", True),
                },
            )
        )

    def _send(self, msg: dict[str, Any]) -> None:
        line = json.dumps(msg, ensure_ascii=False)
        self._stdout.write(line + "\n")
        self._stdout.flush()


def _jsonrpc_result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _jsonrpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
