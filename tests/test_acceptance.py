"""Acceptance tests for installed schema-v1 Bio-Babel producer packages."""

from __future__ import annotations

import pytest

from biobabel._registry.builder import build_registry
from biobabel.mcp.server import BiobabelMCPServer


def _server_with(*packages: str) -> BiobabelMCPServer:
    reg = build_registry()
    names = set(reg.packages)
    missing = set(packages) - names
    if missing:
        details = "; ".join(f"{e.name}: {e.error}" for e in reg.errors[:5])
        pytest.skip(
            "schema-v1 producer contracts not installed for "
            f"{sorted(missing)}. Discovery errors: {details}"
        )
    return BiobabelMCPServer(registry=reg)


def test_ac_ggplot2_describe_aes_includes_keyword_warning():
    server = _server_with("ggplot2_py")
    env = server.call("biobabel.describe_symbol", symbol_id="ggplot2_py.aes")
    assert env["ok"], env
    symbol = env["outputs"]["symbol"]
    text = " ".join(
        [
            symbol.get("signature", ""),
            symbol.get("description", ""),
            " ".join(str(f) for f in symbol.get("failure_fixes", [])),
        ]
    )
    assert "keyword" in text.lower() or "string" in text.lower()


def test_ac_monocle3_describe_symbol_contract():
    server = _server_with("monocle3")
    env = server.call("biobabel.describe_symbol", symbol_id="monocle3.preprocess_cds")
    assert env["ok"], env
    symbol = env["outputs"]["symbol"]
    assert "Size_Factor" in str(symbol["requires"])
    assert "X_pca" in str(symbol["writes"])


def test_ac_monocle3_workflow_is_describable_not_planned():
    server = _server_with("monocle3")
    listed = server.call("biobabel.list_workflows", package="monocle3", task_tag="pseudotime")
    assert listed["ok"], listed
    workflow_ids = {w["id"] for w in listed["outputs"]["workflows"]}
    assert "monocle3.basic_trajectory" in workflow_ids

    described = server.call("biobabel.describe_workflow", workflow_id="monocle3.basic_trajectory")
    assert described["ok"], described
    step_symbols = [s["symbol"] for s in described["outputs"]["workflow"]["steps"]]
    assert "monocle3.learn_graph" in step_symbols
    assert "monocle3.order_cells" in step_symbols
    assert step_symbols.index("monocle3.learn_graph") < step_symbols.index("monocle3.order_cells")


def test_ggplot2_constant_inside_aes_is_flagged():
    server = _server_with("ggplot2_py")
    code = """
from ggplot2_py import ggplot, aes, geom_point
from ggplot2_py.datasets import mpg
p = ggplot(mpg, aes(x="displ", y="hwy")) + geom_point(aes(color="red"))
"""
    env = server.call("biobabel.check_code", code=code, package="ggplot2_py")
    ids = [i.get("anti_pattern_id") for i in env["outputs"]["issues"]]
    assert "ggplot2_py.constant_inside_aes" in ids


def test_grid_py_grob_in_loop_is_flagged():
    server = _server_with("grid_py")
    code = """
from grid_py import rect_grob, Unit, grid_draw
for i in range(10):
    grid_draw(rect_grob(x=Unit(i*0.1, "npc")))
"""
    env = server.call("biobabel.check_code", code=code, package="grid_py")
    ids = [i.get("anti_pattern_id") for i in env["outputs"]["issues"]]
    assert "grid_py.grob_in_loop" in ids


def test_registry_has_onboarded_schema_v1_packages_when_installed():
    reg = build_registry()
    required = {"scales", "grid_py", "gtable_py", "monocle3", "ggplot2_py"}
    if not required <= set(reg.packages):
        details = "; ".join(f"{e.name}: {e.error}" for e in reg.errors[:5])
        pytest.skip(f"schema-v1 producer contracts not installed. Discovery errors: {details}")
    assert not reg.errors, f"unexpected discovery errors: {reg.errors}"
