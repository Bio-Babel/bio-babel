"""Validate a producer package's `_biobabel/` contract directory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import ValidationError

from biobabel.manifest_api import PackageManifest

Severity = Literal["error", "warning", "info"]


@dataclass
class ContractIssue:
    severity: Severity
    code: str
    message: str
    path: str = ""


@dataclass
class ContractValidationReport:
    ok: bool
    package_dir: Path
    contract_class: str | None = None
    manifest: PackageManifest | None = None
    issues: list[ContractIssue] = field(default_factory=list)

    def errors(self) -> list[ContractIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[ContractIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def validate_manifest_only(manifest: PackageManifest) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    if manifest.contract_class in {"analysis", "mixed"} and not manifest.symbols:
        issues.append(
            ContractIssue(
                severity="error",
                code="missing_symbols",
                message="analysis/mixed contracts must declare symbols for agent code generation.",
            )
        )
    if manifest.contract_class in {"grammar", "mixed"} and not (manifest.concepts or manifest.idioms):
        issues.append(
            ContractIssue(
                severity="warning",
                code="missing_composition_knowledge",
                message="grammar/mixed contracts should declare concepts or idioms for composition guidance.",
            )
        )
    if not (manifest.symbols or manifest.workflows or manifest.templates or manifest.idioms):
        issues.append(
            ContractIssue(
                severity="error",
                code="empty_contract",
                message="manifest contains no queryable contract objects.",
            )
        )
    return issues


def validate_package_dir(biobabel_dir: Path) -> ContractValidationReport:
    biobabel_dir = biobabel_dir.resolve()
    if not biobabel_dir.is_dir():
        return ContractValidationReport(
            ok=False,
            package_dir=biobabel_dir,
            issues=[
                ContractIssue(
                    severity="error",
                    code="dir_missing",
                    message=f"_biobabel directory not found at {biobabel_dir}",
                )
            ],
        )

    pkg_yaml = biobabel_dir / "package.yaml"
    if not pkg_yaml.is_file():
        return ContractValidationReport(
            ok=False,
            package_dir=biobabel_dir,
            issues=[
                ContractIssue(
                    severity="error",
                    code="missing_package_yaml",
                    message="package.yaml is mandatory.",
                    path=str(pkg_yaml),
                )
            ],
        )

    try:
        raw = yaml.safe_load(pkg_yaml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return ContractValidationReport(
            ok=False,
            package_dir=biobabel_dir,
            issues=[
                ContractIssue(
                    severity="error",
                    code="package_yaml_unparseable",
                    message=f"package.yaml YAML parse error: {exc}",
                    path=str(pkg_yaml),
                )
            ],
        )

    raw = _hydrate_dir_files(raw, biobabel_dir)
    try:
        manifest = PackageManifest.model_validate(raw)
    except ValidationError as exc:
        return ContractValidationReport(
            ok=False,
            package_dir=biobabel_dir,
            issues=[
                ContractIssue(
                    severity="error",
                    code="schema_invalid",
                    message=str(exc),
                    path=str(pkg_yaml),
                )
            ],
        )

    issues = validate_manifest_only(manifest)
    issues.extend(_check_common_files(biobabel_dir))
    for template in manifest.templates:
        if template.path:
            template_path = (biobabel_dir / template.path).resolve()
            if not template_path.is_file():
                issues.append(
                    ContractIssue(
                        severity="error",
                        code="template_file_missing",
                        message=f"Template '{template.id}' declares path '{template.path}' but file is missing.",
                        path=str(template_path),
                    )
                )

    return ContractValidationReport(
        ok=not any(i.severity == "error" for i in issues),
        package_dir=biobabel_dir,
        contract_class=manifest.contract_class,
        manifest=manifest,
        issues=issues,
    )


def _check_common_files(biobabel_dir: Path) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    for rel in ("skill.md", "examples/smoke.py"):
        path = biobabel_dir / rel
        if not path.is_file():
            issues.append(
                ContractIssue(
                    severity="warning",
                    code=f"missing_{rel.replace('/', '_').replace('.', '_')}",
                    message=f"Recommended file '{rel}' is missing.",
                    path=str(path),
                )
            )
    return issues


_DIR_FIELD_MAP = {
    "symbols": "symbols",
    "workflows": "workflows",
    "templates": "templates",
    "concepts": "concepts",
    "idioms": "idioms",
    "anti_patterns": "anti_patterns",
    "compositions": "compositions",
}


def _hydrate_dir_files(raw: dict, biobabel_dir: Path) -> dict:
    for subdir, field_name in _DIR_FIELD_MAP.items():
        sub_path = biobabel_dir / subdir
        if not sub_path.is_dir():
            continue
        items: list[dict] = list(raw.get(field_name, []) or [])
        for yaml_file in sorted(sub_path.glob("*.yaml")):
            loaded = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if loaded is None:
                continue
            if isinstance(loaded, list):
                items.extend(loaded)
            else:
                items.append(loaded)
        if items:
            raw[field_name] = items
    return raw
