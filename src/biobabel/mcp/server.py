"""biobabel MCP server — read-only contract tools over a dispatch table."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from biobabel._registry.builder import Registry, build_registry
from biobabel.mcp.tools import concept, discovery, meta, validation

ToolHandler = Callable[..., dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    group: str
    handler: ToolHandler
    description: str


class BiobabelMCPServer:
    def __init__(self, registry: Registry | None = None) -> None:
        self.registry = registry or build_registry()
        self._tools: dict[str, ToolSpec] = {}
        self._wire()

    def _wire(self) -> None:
        reg = self.registry

        self._add(
            "biobabel.list_packages",
            "contracts",
            lambda **kw: discovery.list_packages(reg, **kw),
            "List registered Bio-Babel packages with agent ranking signals",
        )
        self._add(
            "biobabel.describe_package",
            "contracts",
            lambda **kw: discovery.describe_package(reg, **kw),
            "Return the full package manifest",
        )
        self._add(
            "biobabel.search_contracts",
            "contracts",
            lambda **kw: discovery.search_contracts(reg, **kw),
            "Lexical search over symbols, workflows, templates, concepts, and idioms",
        )
        self._add(
            "biobabel.list_workflows",
            "contracts",
            lambda **kw: discovery.list_workflows(reg, **kw),
            "List reference workflows; does not choose a plan",
        )
        self._add(
            "biobabel.describe_workflow",
            "contracts",
            lambda **kw: discovery.describe_workflow(reg, **kw),
            "Describe one reference workflow",
        )
        self._add(
            "biobabel.list_symbols",
            "contracts",
            lambda **kw: discovery.list_symbols(reg, **kw),
            "List callable/class/constant symbol contracts",
        )
        self._add(
            "biobabel.describe_symbol",
            "contracts",
            lambda **kw: discovery.describe_symbol(reg, **kw),
            "Describe one symbol contract with exact calling guidance",
        )
        self._add(
            "biobabel.list_templates",
            "contracts",
            lambda **kw: discovery.list_templates(reg, **kw),
            "List reusable script/function templates",
        )
        self._add(
            "biobabel.describe_template",
            "contracts",
            lambda **kw: discovery.describe_template(reg, **kw),
            "Describe one reusable template",
        )
        self._add(
            "biobabel.describe_concept",
            "concept",
            lambda **kw: concept.describe_concept(reg, **kw),
            "Describe one conceptual invariant",
        )
        self._add(
            "biobabel.list_idioms",
            "concept",
            lambda **kw: concept.list_idioms(reg, **kw),
            "List compositional idioms",
        )
        self._add(
            "biobabel.describe_idiom",
            "concept",
            lambda **kw: concept.describe_idiom(reg, **kw),
            "Describe one compositional idiom with code template",
        )
        self._add(
            "biobabel.check_code",
            "validation",
            lambda **kw: validation.check_code(reg, **kw),
            "Semantic lint: AST policy scan plus package anti-patterns",
        )
        self._add(
            "biobabel.list_tools",
            "meta",
            lambda **kw: meta.list_tools(list(self._tools)),
            "List all biobabel MCP tools",
        )
        self._add(
            "biobabel.health",
            "meta",
            lambda **kw: meta.health(reg),
            "Registry health snapshot",
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
