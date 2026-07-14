"""Claude Code plugin bundle: structural invariants + hook I/O contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN = REPO_ROOT / "plugin" / "biobabel"
HOOK = PLUGIN / "hooks" / "r-paste-detector.py"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_declares_name():
    manifest = _load(PLUGIN / ".claude-plugin" / "plugin.json")
    assert manifest["name"] == "biobabel"


def test_mcp_json_uses_mcpservers_wrapper():
    mcp = _load(PLUGIN / ".mcp.json")
    assert mcp["mcpServers"]["biobabel"]["command"] == "biobabel-mcp"


def test_hooks_json_has_inner_hooks_array():
    hooks = _load(PLUGIN / "hooks" / "hooks.json")
    entries = hooks["hooks"]["UserPromptSubmit"]
    assert isinstance(entries, list) and len(entries) == 1
    inner = entries[0]["hooks"]
    assert isinstance(inner, list)
    assert inner[0]["type"] == "command"
    cmd = inner[0]["command"]
    assert "${CLAUDE_PLUGIN_ROOT}" in cmd
    assert cmd.endswith("hooks/r-paste-detector.py")
    assert "matcher" not in entries[0]


def test_marketplace_points_at_claude_bundle():
    mp = _load(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    entry = mp["plugins"][0]
    assert entry["name"] == "biobabel"
    assert (REPO_ROOT / entry["source"]).resolve() == PLUGIN


def test_skills_are_present_with_frontmatter():
    skill_dirs = sorted(p.name for p in (PLUGIN / "skills").iterdir() if p.is_dir())
    assert "biobabel-overview" in skill_dirs
    for name in skill_dirs:
        text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---"), f"{name}: missing frontmatter"
        assert "name:" in text and "description:" in text


def _run_hook(prompt: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
    )


def test_hook_emits_plain_text_context_on_r_syntax():
    res = _run_hook("cds <- library(monocle3)")
    assert res.returncode == 0
    assert "biobabel" in res.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(res.stdout)


def test_hook_recognizes_ggplot_aes():
    res = _run_hook("ggplot(df, aes(x, y)) + geom_point()")
    assert "ggplot2_py" in res.stdout


def test_hook_is_silent_on_plain_prompt():
    res = _run_hook("please summarize this dataframe for me")
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_hook_exits_zero_on_garbage_stdin():
    res = subprocess.run(
        [sys.executable, str(HOOK)], input="not json", capture_output=True, text=True
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
