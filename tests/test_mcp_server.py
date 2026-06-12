"""MCP server: schema v1 tool wiring and envelopes."""

from __future__ import annotations

from biobabel.mcp.server import BiobabelMCPServer


def test_server_wires_contract_server_tools(registry):
    server = BiobabelMCPServer(registry=registry)
    assert server.tool_count == 16
    assert "biobabel.match_failure" in server.tool_names
    assert "biobabel.plan_workflow" not in server.tool_names
    assert "biobabel.check_prerequisites" not in server.tool_names
    assert "biobabel.load_adata" not in server.tool_names
    assert "biobabel.run_recipe" not in server.tool_names
    assert "biobabel.list_traces" not in server.tool_names
    assert "biobabel.run_code" not in server.tool_names


def test_list_packages_envelope_surfaces_agent_ranking_signals(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.list_packages")
    assert env["ok"]
    packages = env["outputs"]["packages"]
    assert {p["import_name"] for p in packages} >= {"grid_py", "monocle3_py"}
    sample = packages[0]
    for field in ("triggers", "task_tags", "capabilities", "domain_tags", "not_when", "foundation"):
        assert field in sample


def test_search_contracts_tool(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.search_contracts", query="pseudotime size factors")
    assert env["ok"]
    assert any(h["id"] == "monocle3.estimate_size_factors" for h in env["outputs"]["hits"])


def test_workflow_and_symbol_lookup(registry):
    server = BiobabelMCPServer(registry=registry)
    wf = server.call("biobabel.describe_workflow", workflow_id="monocle3.basic_trajectory")
    assert wf["ok"], wf
    assert wf["outputs"]["workflow"]["steps"][0]["symbol"] == "monocle3.estimate_size_factors"

    sym = server.call("biobabel.describe_symbol", symbol_id="monocle3.preprocess_cds")
    assert sym["ok"], sym
    assert "preprocess_cds(" in sym["outputs"]["symbol"]["signature"]


def test_templates_are_queryable(registry):
    server = BiobabelMCPServer(registry=registry)
    listed = server.call("biobabel.list_templates", package="monocle3_py")
    assert listed["ok"]
    assert listed["outputs"]["templates"][0]["id"] == "monocle3.basic_script"

    described = server.call("biobabel.describe_template", template_id="monocle3.basic_script")
    assert described["ok"]
    assert described["outputs"]["template"]["path"] == "templates/basic.py"


def test_describe_concept_and_idiom(registry):
    server = BiobabelMCPServer(registry=registry)
    concept = server.call("biobabel.describe_concept", concept_id="grid_py.Viewport")
    assert concept["ok"]
    assert concept["outputs"]["concept"]["name"] == "Viewport"

    idiom = server.call("biobabel.describe_idiom", idiom_id="grid_py.push_draw_pop")
    assert idiom["ok"]
    assert "push_viewport" in idiom["outputs"]["idiom"]["code_template"]


def test_check_code_flags_anti_pattern(registry):
    server = BiobabelMCPServer(registry=registry)
    code = """
from grid_py import rect_grob, Unit, grid_draw
for i in range(10):
    grid_draw(rect_grob(x=Unit(i*0.1, "npc")))
"""
    env = server.call("biobabel.check_code", code=code, package="grid_py")
    assert env["ok"]
    assert any(i.get("anti_pattern_id") == "grid_py.grob_in_loop" for i in env["outputs"]["issues"])


def test_unknown_tool_returns_error_envelope(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.no_such_tool")
    assert env["ok"] is False
    assert env["error_code"] == "unknown_tool"


def test_list_tools_returns_all(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.list_tools")
    assert env["ok"]
    assert len(env["outputs"]["tools"]) == 16


def test_health(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.health")
    assert env["ok"]
    assert env["outputs"]["packages"] == 2
    assert env["outputs"]["symbols"] >= 1
