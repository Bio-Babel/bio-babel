"""Stdio transport: JSON-RPC wire protocol over the read-only tool surface.

All biobabel tools return a single result envelope, so the transport has no
progress / streaming path — every ``tools/call`` yields exactly one result.
"""

from __future__ import annotations

import io
import json

from biobabel.mcp.server import BiobabelMCPServer
from biobabel.mcp.transports.stdio import StdioTransport


def _drive(server: BiobabelMCPServer, *requests: dict) -> list[dict]:
    """Feed *requests* to a StdioTransport and return parsed responses."""
    in_buf = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
    out_buf = io.StringIO()
    StdioTransport(server, stdin=in_buf, stdout=out_buf).serve_forever()
    return [json.loads(line) for line in out_buf.getvalue().splitlines() if line]


def test_initialize_reports_server_info(registry):
    server = BiobabelMCPServer(registry=registry)
    responses = _drive(server, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert len(responses) == 1
    result = responses[0]["result"]
    assert result["serverInfo"]["name"] == "biobabel"
    assert "protocolVersion" in result


def test_tools_list_returns_every_wired_tool(registry):
    server = BiobabelMCPServer(registry=registry)
    responses = _drive(server, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in responses[0]["result"]["tools"]}
    assert names == set(server.tool_names)
    assert "biobabel.run_code" not in names


def test_tools_list_advertises_real_input_schemas(registry):
    server = BiobabelMCPServer(registry=registry)
    responses = _drive(server, {"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
    schemas = {t["name"]: t["inputSchema"] for t in responses[0]["result"]["tools"]}

    describe_symbol = schemas["biobabel.describe_symbol"]
    assert describe_symbol["properties"] == {"symbol_id": {"type": "string"}}
    assert describe_symbol["required"] == ["symbol_id"]

    # No tool keeps the old empty-but-permissive placeholder schema.
    assert all(s["additionalProperties"] is False for s in schemas.values())
    assert all("properties" in s for s in schemas.values())


def test_tools_call_returns_single_result_envelope(registry):
    server = BiobabelMCPServer(registry=registry)
    responses = _drive(server, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "biobabel.list_packages", "arguments": {}},
    })
    assert len(responses) == 1
    assert responses[0]["id"] == 3
    payload = json.loads(responses[0]["result"]["content"][0]["text"])
    assert payload["ok"]
    assert "packages" in payload["outputs"]


def test_tools_call_error_is_marked_iserror(registry):
    server = BiobabelMCPServer(registry=registry)
    responses = _drive(server, {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "biobabel.no_such_tool", "arguments": {}},
    })
    result = responses[0]["result"]
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert payload["error_code"] == "unknown_tool"


def test_unknown_method_returns_jsonrpc_error(registry):
    server = BiobabelMCPServer(registry=registry)
    responses = _drive(server, {"jsonrpc": "2.0", "id": 5, "method": "no/such/method"})
    assert responses[0]["error"]["code"] == -32601


def test_parse_error_is_reported(registry):
    server = BiobabelMCPServer(registry=registry)
    in_buf = io.StringIO("{not json\n")
    out_buf = io.StringIO()
    StdioTransport(server, stdin=in_buf, stdout=out_buf).serve_forever()
    responses = [json.loads(line) for line in out_buf.getvalue().splitlines() if line]
    assert responses[0]["error"]["code"] == -32700
