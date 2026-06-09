"""Pydantic invariants for schema v1."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from biobabel.manifest_api import (
    AntiPatternDetection,
    PackageManifest,
    SymbolContract,
    WorkflowContract,
    WorkflowStep,
)


def test_schema_version_is_reset_to_one():
    m = PackageManifest(
        repo="x",
        distribution="x",
        import_name="x",
        display_name="x",
        contract_class="analysis",
        symbols=[SymbolContract(id="x.fn", import_path="x.fn")],
    )
    assert m.schema_version == 1


def test_package_manifest_rejects_non_v1_schema_version():
    base = {
        "repo": "x",
        "distribution": "x",
        "import_name": "x",
        "display_name": "x",
        "contract_class": "analysis",
        "symbols": [{"id": "x.fn", "import_path": "x.fn"}],
    }
    for bad in (2, 3, 99):
        with pytest.raises(ValidationError, match="schema_version"):
            PackageManifest(schema_version=bad, **base)


def test_symbol_requires_and_writes_are_free_text_facts():
    s = SymbolContract(
        id="pkg.reduce_dimension",
        import_path="pkg.reduce_dimension",
        requires=["adata.obs['Size_Factor'] exists", "raw counts in selected layer"],
        writes=["adata.obsm['X_dr']"],
    )
    assert "raw counts" in s.requires[1]
    assert s.writes == ["adata.obsm['X_dr']"]


def test_symbol_purpose_fills_description():
    s = SymbolContract(id="pkg.fn", import_path="pkg.fn", purpose="Do the thing.")
    assert s.description == "Do the thing."


def test_workflow_steps_reference_symbols_not_calls():
    wf = WorkflowContract(
        id="pkg.basic",
        steps=[WorkflowStep(symbol="pkg.fn", purpose="First step")],
    )
    assert wf.steps[0].symbol == "pkg.fn"


def test_anti_pattern_detection_requires_at_least_one_rule():
    with pytest.raises(ValidationError, match="at least one of"):
        AntiPatternDetection()


def test_anti_pattern_detection_accepts_detector_id():
    d = AntiPatternDetection(detector_id="rgrid.for_loop_calls", args={"calls": ["x"]})
    assert d.detector_id == "rgrid.for_loop_calls"
    assert d.args == {"calls": ["x"]}


def test_anti_pattern_detection_accepts_regex_only():
    d = AntiPatternDetection(regex=r"foo")
    assert d.regex == "foo"
    assert d.detector_id == ""


def test_unknown_manifest_fields_are_rejected():
    with pytest.raises(ValidationError, match="unexpected_field"):
        PackageManifest(
            repo="x",
            distribution="x",
            import_name="x",
            display_name="x",
            contract_class="analysis",
            unexpected_field="x",
        )


def test_json_schema_round_trip():
    schema = PackageManifest.model_json_schema()
    assert schema["title"] == "PackageManifest"
    properties = schema["properties"]
    for name in ("contract_class", "symbols", "workflows", "templates"):
        assert name in properties
