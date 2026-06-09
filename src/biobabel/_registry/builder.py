"""Registry: indexed view over discovered manifests and detectors."""

from __future__ import annotations

from dataclasses import dataclass, field

from biobabel._registry.discovery import (
    DiscoveredDetector,
    DiscoveredManifest,
    DiscoveryError,
    discover,
    discover_detectors,
)
from biobabel.manifest_api import (
    AntiPatternSpec,
    ConceptSpec,
    IdiomSpec,
    PackageManifest,
    SymbolContract,
    TemplateSpec,
    WorkflowContract,
)


def _record_duplicate(
    errors: list[DiscoveryError],
    *,
    kind_label: str,
    key: str,
    keeper_distribution: str,
    skipped_distribution: str,
) -> None:
    errors.append(
        DiscoveryError(
            name=key,
            distribution=skipped_distribution,
            error=(
                f"duplicate {kind_label} {key!r}: first registered by "
                f"{keeper_distribution!r}, now also declared by "
                f"{skipped_distribution!r}; keeping first, ignoring second"
            ),
            kind="duplicate",
        )
    )


@dataclass
class Registry:
    packages: dict[str, DiscoveredManifest] = field(default_factory=dict)
    detectors: dict[str, DiscoveredDetector] = field(default_factory=dict)
    errors: list[DiscoveryError] = field(default_factory=list)

    _symbol_by_id: dict[str, tuple[str, SymbolContract]] = field(default_factory=dict)
    _workflow_by_id: dict[str, tuple[str, WorkflowContract]] = field(default_factory=dict)
    _template_by_id: dict[str, tuple[str, TemplateSpec]] = field(default_factory=dict)
    _concept_by_id: dict[str, tuple[str, ConceptSpec]] = field(default_factory=dict)
    _idiom_by_id: dict[str, tuple[str, IdiomSpec]] = field(default_factory=dict)
    _anti_pattern_by_id: dict[str, tuple[str, AntiPatternSpec]] = field(default_factory=dict)

    def manifest(self, import_name: str) -> PackageManifest | None:
        entry = self.packages.get(import_name)
        return entry.manifest if entry else None

    def list_packages(
        self,
        *,
        contract_class: str | None = None,
        tier: int | None = None,
        maturity: str | None = None,
    ) -> list[DiscoveredManifest]:
        out = list(self.packages.values())
        if contract_class:
            out = [d for d in out if d.manifest.contract_class == contract_class]
        if tier is not None:
            out = [d for d in out if d.manifest.tier == tier]
        if maturity:
            out = [d for d in out if d.manifest.maturity == maturity]
        return out

    def list_symbols(self, package: str | None = None) -> list[tuple[str, SymbolContract]]:
        return [
            (pkg, symbol)
            for pkg, symbol in self._symbol_by_id.values()
            if package is None or pkg == package
        ]

    def list_workflows(self, package: str | None = None) -> list[tuple[str, WorkflowContract]]:
        return [
            (pkg, workflow)
            for pkg, workflow in self._workflow_by_id.values()
            if package is None or pkg == package
        ]

    def list_templates(self, package: str | None = None) -> list[tuple[str, TemplateSpec]]:
        return [
            (pkg, template)
            for pkg, template in self._template_by_id.values()
            if package is None or pkg == package
        ]

    def symbol(self, symbol_id: str) -> tuple[str, SymbolContract] | None:
        return self._symbol_by_id.get(symbol_id)

    def workflow(self, workflow_id: str) -> tuple[str, WorkflowContract] | None:
        return self._workflow_by_id.get(workflow_id)

    def template(self, template_id: str) -> tuple[str, TemplateSpec] | None:
        return self._template_by_id.get(template_id)

    def concept(self, concept_id: str) -> tuple[str, ConceptSpec] | None:
        return self._concept_by_id.get(concept_id)

    def idiom(self, idiom_id: str) -> tuple[str, IdiomSpec] | None:
        return self._idiom_by_id.get(idiom_id)

    def anti_pattern(self, anti_pattern_id: str) -> tuple[str, AntiPatternSpec] | None:
        return self._anti_pattern_by_id.get(anti_pattern_id)

    def detector(self, detector_id: str) -> DiscoveredDetector | None:
        return self.detectors.get(detector_id)

    def all_idioms(self) -> list[tuple[str, IdiomSpec]]:
        return list(self._idiom_by_id.values())

    def all_anti_patterns(self) -> list[tuple[str, AntiPatternSpec]]:
        return list(self._anti_pattern_by_id.values())


def build_registry() -> Registry:
    manifest_successes, manifest_errors = discover()
    detector_successes, detector_errors = discover_detectors()
    reg = Registry(errors=list(manifest_errors) + list(detector_errors))

    for d in manifest_successes:
        if d.import_name in reg.packages:
            _record_duplicate(
                reg.errors,
                kind_label="package import_name",
                key=d.import_name,
                keeper_distribution=reg.packages[d.import_name].distribution,
                skipped_distribution=d.distribution,
            )
            continue

        reg.packages[d.import_name] = d
        m = d.manifest
        _index_many(reg, d, "symbol", m.symbols, reg._symbol_by_id)
        _index_many(reg, d, "workflow", m.workflows, reg._workflow_by_id)
        _index_many(reg, d, "template", m.templates, reg._template_by_id)
        _index_many(reg, d, "concept", m.concepts, reg._concept_by_id)
        _index_many(reg, d, "idiom", m.idioms, reg._idiom_by_id)
        _index_many(reg, d, "anti_pattern", m.anti_patterns, reg._anti_pattern_by_id)

    for dd in detector_successes:
        if dd.detector_id in reg.detectors:
            _record_duplicate(
                reg.errors,
                kind_label="detector id",
                key=dd.detector_id,
                keeper_distribution=reg.detectors[dd.detector_id].distribution,
                skipped_distribution=dd.distribution,
            )
            continue
        reg.detectors[dd.detector_id] = dd

    return reg


def _index_many(reg: Registry, d: DiscoveredManifest, label: str, items: list, index: dict) -> None:
    for item in items:
        if item.id in index:
            existing_pkg, _ = index[item.id]
            _record_duplicate(
                reg.errors,
                kind_label=f"{label} id",
                key=item.id,
                keeper_distribution=reg.packages[existing_pkg].distribution,
                skipped_distribution=d.distribution,
            )
            continue
        index[item.id] = (d.import_name, item)
