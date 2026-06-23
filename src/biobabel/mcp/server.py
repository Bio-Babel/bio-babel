"""biobabel MCP server — read-only contract tools over a dispatch table."""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from biobabel._registry.builder import Registry, build_registry
from biobabel.mcp.schema import build_input_schema
from biobabel.mcp.tools import concept, discovery, validation

ToolHandler = Callable[..., dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    group: str
    handler: ToolHandler
    description: str
    input_schema: dict[str, Any]


class BiobabelMCPServer:
    def __init__(self, registry: Registry | None = None) -> None:
        self.registry = registry or build_registry()
        self._tools: dict[str, ToolSpec] = {}
        self._wire()

    def _wire(self) -> None:
        reg = self.registry
        bind = functools.partial  # pre-bind the registry; signature stays introspectable

        self._add(
            "biobabel.list_packages",
            "contracts",
            bind(discovery.list_packages, reg),
            "List registered Bio-Babel packages",
        )
        self._add(
            "biobabel.describe_package",
            "contracts",
            bind(discovery.describe_package, reg),
            "Return the full package manifest",
        )
        self._add(
            "biobabel.list_workflows",
            "contracts",
            bind(discovery.list_workflows, reg),
            "List reference workflows; does not choose a plan",
        )
        self._add(
            "biobabel.describe_workflow",
            "contracts",
            bind(discovery.describe_workflow, reg),
            "Describe one reference workflow",
        )
        self._add(
            "biobabel.list_symbols",
            "contracts",
            bind(discovery.list_symbols, reg),
            "List callable/class/constant symbol contracts",
        )
        self._add(
            "biobabel.describe_symbol",
            "contracts",
            bind(discovery.describe_symbol, reg),
            "Describe one symbol contract with exact calling guidance",
        )
        self._add(
            "biobabel.list_templates",
            "contracts",
            bind(discovery.list_templates, reg),
            "List reusable script/function templates",
        )
        self._add(
            "biobabel.describe_template",
            "contracts",
            bind(discovery.describe_template, reg),
            "Describe one reusable template",
        )
        self._add(
            "biobabel.describe_concept",
            "concept",
            bind(concept.describe_concept, reg),
            "Describe one conceptual invariant",
        )
        self._add(
            "biobabel.list_idioms",
            "concept",
            bind(concept.list_idioms, reg),
            "List compositional idioms",
        )
        self._add(
            "biobabel.describe_idiom",
            "concept",
            bind(concept.describe_idiom, reg),
            "Describe one compositional idiom with code template",
        )
        self._add(
            "biobabel.check_code",
            "validation",
            bind(validation.check_code, reg),
            "Semantic lint: AST policy scan plus package anti-patterns",
        )

    def _add(
        self,
        name: str,
        group: str,
        handler: ToolHandler,
        description: str,
    ) -> None:
        self._tools[name] = ToolSpec(
            name=name,
            group=group,
            handler=handler,
            description=description,
            input_schema=build_input_schema(handler),
        )

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def tool(self, name: str) -> ToolSpec:
        return self._tools[name]

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        if name not in self._tools:
            from biobabel.mcp.envelope import error

            return error(name, error_code="unknown_tool", message=f"no tool '{name}'")
        return self._tools[name].handler(**kwargs)


def build_server() -> BiobabelMCPServer:
    return BiobabelMCPServer()
