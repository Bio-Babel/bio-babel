"""inputSchema generation from handler signatures.

Covers the type-mapping matrix the handlers actually use and confirms the
pre-bound ``registry`` never leaks into the agent-facing schema.
"""

from __future__ import annotations

import functools
from typing import Any, Literal

from biobabel.mcp.schema import build_input_schema
from biobabel.mcp.server import BiobabelMCPServer


def _required(registry: Any, *, query: str) -> dict[str, Any]:
    return {}


def _optionals(
    registry: Any,
    *,
    package: str | None = None,
    tier: int | None = None,
    kinds: list[str] | None = None,
    flag: bool = False,
) -> dict[str, Any]:
    return {}


def _literal(registry: Any, *, klass: Literal["a", "b", "c"] | None = None) -> dict[str, Any]:
    return {}


def _no_agent_args(registry: Any) -> dict[str, Any]:
    return {}


def test_required_param_is_typed_and_required():
    schema = build_input_schema(functools.partial(_required, None))
    assert schema["type"] == "object"
    assert schema["properties"] == {"query": {"type": "string"}}
    assert schema["required"] == ["query"]
    assert schema["additionalProperties"] is False


def test_optionals_are_typed_but_not_required():
    props = build_input_schema(functools.partial(_optionals, None))["properties"]
    assert props["package"] == {"type": "string"}
    assert props["tier"] == {"type": "integer"}
    assert props["kinds"] == {"type": "array", "items": {"type": "string"}}
    assert props["flag"] == {"type": "boolean"}


def test_all_optional_params_omit_required_key():
    assert "required" not in build_input_schema(functools.partial(_optionals, None))


def test_literal_becomes_enum():
    klass = build_input_schema(functools.partial(_literal, None))["properties"]["klass"]
    assert klass["enum"] == ["a", "b", "c"]
    assert klass["type"] == "string"


def test_no_agent_args_yields_empty_properties():
    schema = build_input_schema(functools.partial(_no_agent_args, None))
    assert schema["properties"] == {}
    assert "required" not in schema


def test_prebound_registry_is_never_exposed():
    assert "registry" not in build_input_schema(functools.partial(_optionals, None))["properties"]


def test_wired_tools_advertise_real_schemas(registry):
    server = BiobabelMCPServer(registry=registry)

    describe_symbol = server.tool("biobabel.describe_symbol").input_schema
    assert describe_symbol["properties"] == {"symbol_id": {"type": "string"}}
    assert describe_symbol["required"] == ["symbol_id"]

    list_packages = server.tool("biobabel.list_packages").input_schema
    assert list_packages["properties"]["contract_class"]["enum"] == ["analysis", "grammar", "mixed"]
    assert list_packages["properties"]["tier"] == {"type": "integer"}
    assert "required" not in list_packages  # every filter is optional

    # meta tools take no agent arguments
    assert server.tool("biobabel.health").input_schema["properties"] == {}
    assert server.tool("biobabel.list_tools").input_schema["properties"] == {}
