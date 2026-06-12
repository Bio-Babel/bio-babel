"""biobabel.match_failure — map a runtime traceback to curated failure fixes.

The read-only layer never executes code; this tool interprets the traceback the
agent produced with its own tools and routes it back to the producer's curated
``failure_fixes`` (and relevant anti-patterns).
"""

from __future__ import annotations

from biobabel._concept.failure_match import match_failures
from biobabel.mcp.server import BiobabelMCPServer

_TRACEBACK = """Traceback (most recent call last):
  File "analysis.py", line 12, in <module>
    monocle3.preprocess_cds(adata, num_dim=50)
  File ".../monocle3/preprocessing.py", line 88, in preprocess_cds
    sf = adata.obs['Size_Factor']
KeyError: 'Size_Factor'
"""


def test_match_failures_finds_curated_fix(registry):
    matches = match_failures(registry, _TRACEBACK)
    assert matches, "expected at least one curated match"
    top = matches[0]
    assert top.source == "failure_fix"
    assert top.item_id == "monocle3.preprocess_cds"
    assert "monocle3.estimate_size_factors" in top.suggest


def test_match_failures_ranks_by_descending_overlap(registry):
    scores = [m.score for m in match_failures(registry, _TRACEBACK)]
    assert scores == sorted(scores, reverse=True)


def test_match_failures_empty_text_returns_nothing(registry):
    assert match_failures(registry, "   ") == []


def test_match_failures_respects_package_filter(registry):
    # The curated fix lives on a monocle3_py symbol; filtering to grid_py drops it.
    assert not [
        m for m in match_failures(registry, _TRACEBACK, package="grid_py")
        if m.source == "failure_fix"
    ]


def test_match_failures_can_match_anti_pattern(registry):
    # grid_py anti-pattern grob_in_loop: why_bad="N draws instead of 1."
    matches = match_failures(registry, "performance issue: N draws instead of 1 in a loop")
    assert any(
        m.source == "anti_pattern" and m.item_id == "grid_py.grob_in_loop" for m in matches
    )


def test_match_failure_tool_via_server(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.match_failure", error_text=_TRACEBACK)
    assert env["ok"], env
    matches = env["outputs"]["matches"]
    assert any(
        m["id"] == "monocle3.preprocess_cds"
        and "monocle3.estimate_size_factors" in m["suggest"]
        for m in matches
    )


def test_match_failure_tool_empty_error_returns_error_envelope(registry):
    server = BiobabelMCPServer(registry=registry)
    env = server.call("biobabel.match_failure", error_text="")
    assert env["ok"] is False
    assert env["error_code"] == "empty_error"


def test_match_failure_tool_is_registered_with_schema(registry):
    server = BiobabelMCPServer(registry=registry)
    assert "biobabel.match_failure" in server.tool_names
    schema = server.tool("biobabel.match_failure").input_schema
    assert schema["properties"]["error_text"] == {"type": "string"}
    assert schema["properties"]["limit"] == {"type": "integer"}
    assert schema["required"] == ["error_text"]
