"""Meta tools."""

from __future__ import annotations

from typing import Any

from biobabel._registry.builder import Registry
from biobabel.mcp.envelope import success


def list_tools(tool_names: list[str]) -> dict[str, Any]:
    return success(
        "biobabel.list_tools",
        summary=f"{len(tool_names)} tools",
        outputs={"tools": sorted(tool_names)},
    )


def health(registry: Registry) -> dict[str, Any]:
    warnings = [
        f"[{err.kind}] {err.name} ({err.distribution}): {err.error}"
        for err in registry.errors
    ]
    return success(
        "biobabel.health",
        summary=f"{len(registry.packages)} packages, {len(warnings)} discovery warning(s)",
        outputs={
            "packages": len(registry.packages),
            "symbols": len(registry._symbol_by_id),
            "workflows": len(registry._workflow_by_id),
            "templates": len(registry._template_by_id),
            "concepts": len(registry._concept_by_id),
            "idioms": len(registry._idiom_by_id),
            "anti_patterns": len(registry._anti_pattern_by_id),
            "detectors": len(registry.detectors),
            "discovery_errors": [err.__dict__ for err in registry.errors],
        },
        warnings=warnings,
    )
