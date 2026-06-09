"""Contract discovery and lookup tools."""

from __future__ import annotations

from typing import Any

from biobabel._registry.builder import Registry
from biobabel._registry.search import search_contracts as _search_contracts
from biobabel.mcp.envelope import error, success


def list_packages(
    registry: Registry,
    *,
    contract_class: str | None = None,
    tier: int | None = None,
    maturity: str | None = None,
) -> dict[str, Any]:
    rows = []
    for d in registry.list_packages(contract_class=contract_class, tier=tier, maturity=maturity):
        m = d.manifest
        rows.append(
            {
                "import_name": d.import_name,
                "distribution": d.distribution,
                "version": d.distribution_version,
                "contract_class": m.contract_class,
                "tier": m.tier,
                "maturity": m.maturity,
                "display_name": m.display_name,
                "triggers": list(m.triggers),
                "task_tags": list(m.task_tags),
                "capabilities": list(m.capabilities),
                "domain_tags": list(m.domain_tags),
                "not_when": list(m.not_when),
                "foundation": list(m.foundation),
            }
        )
    return success(
        "biobabel.list_packages",
        summary=f"{len(rows)} package(s) registered",
        outputs={"packages": rows, "errors": [e.__dict__ for e in registry.errors]},
    )


def describe_package(registry: Registry, *, import_name: str) -> dict[str, Any]:
    d = registry.packages.get(import_name)
    if d is None:
        return error(
            "biobabel.describe_package",
            error_code="not_found",
            message=f"no package registered under import name '{import_name}'",
        )
    return success(
        "biobabel.describe_package",
        summary=f"{d.manifest.display_name} ({d.manifest.contract_class})",
        outputs={"manifest": d.manifest.model_dump(mode="json")},
    )


def search_contracts(
    registry: Registry,
    *,
    query: str,
    package: str | None = None,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    if not query.strip():
        return error("biobabel.search_contracts", error_code="empty_query", message="query must be non-empty")
    try:
        if kinds is None:
            hits = _search_contracts(registry, query, package=package)
        else:
            hits = _search_contracts(registry, query, package=package, kinds=kinds)
    except ValueError as exc:
        return error("biobabel.search_contracts", error_code="bad_kinds", message=str(exc))
    return success("biobabel.search_contracts", summary=f"{len(hits)} hit(s)", outputs={"hits": hits})


def list_workflows(registry: Registry, *, package: str | None = None, task_tag: str | None = None) -> dict[str, Any]:
    rows = []
    for pkg, workflow in registry.list_workflows(package=package):
        if task_tag and task_tag not in workflow.task_tags:
            continue
        rows.append(
            {
                "package": pkg,
                "id": workflow.id,
                "title": workflow.title,
                "task_tags": list(workflow.task_tags),
                "description": workflow.description,
            }
        )
    return success("biobabel.list_workflows", summary=f"{len(rows)} workflow(s)", outputs={"workflows": rows})


def describe_workflow(registry: Registry, *, workflow_id: str) -> dict[str, Any]:
    hit = registry.workflow(workflow_id)
    if hit is None:
        return error(
            "biobabel.describe_workflow",
            error_code="not_found",
            message=f"no WorkflowContract with id '{workflow_id}'",
        )
    pkg, workflow = hit
    return success(
        "biobabel.describe_workflow",
        summary=workflow.title or workflow.id,
        outputs={"package": pkg, "workflow": workflow.model_dump(mode="json")},
    )


def list_symbols(registry: Registry, *, package: str | None = None, kind: str | None = None) -> dict[str, Any]:
    rows = []
    for pkg, symbol in registry.list_symbols(package=package):
        if kind and symbol.kind != kind:
            continue
        rows.append(
            {
                "package": pkg,
                "id": symbol.id,
                "kind": symbol.kind,
                "signature": symbol.signature,
                "summary": symbol.description or symbol.purpose,
            }
        )
    return success("biobabel.list_symbols", summary=f"{len(rows)} symbol(s)", outputs={"symbols": rows})


def describe_symbol(registry: Registry, *, symbol_id: str) -> dict[str, Any]:
    hit = registry.symbol(symbol_id)
    if hit is None:
        return error(
            "biobabel.describe_symbol",
            error_code="not_found",
            message=f"no SymbolContract with id '{symbol_id}'",
        )
    pkg, symbol = hit
    return success(
        "biobabel.describe_symbol",
        summary=symbol.signature or symbol.id,
        outputs={"package": pkg, "symbol": symbol.model_dump(mode="json")},
    )


def list_templates(registry: Registry, *, package: str | None = None, task_tag: str | None = None) -> dict[str, Any]:
    rows = []
    for pkg, template in registry.list_templates(package=package):
        if task_tag and task_tag not in template.task_tags:
            continue
        rows.append(
            {
                "package": pkg,
                "id": template.id,
                "path": template.path,
                "task_tags": list(template.task_tags),
                "description": template.description,
            }
        )
    return success("biobabel.list_templates", summary=f"{len(rows)} template(s)", outputs={"templates": rows})


def describe_template(registry: Registry, *, template_id: str) -> dict[str, Any]:
    hit = registry.template(template_id)
    if hit is None:
        return error(
            "biobabel.describe_template",
            error_code="not_found",
            message=f"no TemplateSpec with id '{template_id}'",
        )
    pkg, template = hit
    return success(
        "biobabel.describe_template",
        summary=template.description or template.id,
        outputs={"package": pkg, "template": template.model_dump(mode="json")},
    )
