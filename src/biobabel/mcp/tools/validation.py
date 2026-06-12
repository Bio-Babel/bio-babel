"""Group 5 — Validation (1 tool: check_code)."""

from __future__ import annotations

from typing import Any

from biobabel._concept.anti_pattern_detector import detect_anti_patterns
from biobabel._concept.failure_match import match_failures
from biobabel._concept.policy import scan_code
from biobabel._registry.builder import Registry
from biobabel.mcp.envelope import error, success


def check_code(
    registry: Registry,
    *,
    code: str,
    package: str | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    scan = scan_code(code, extra_allow=list(registry.packages.keys()))
    for v in scan.violations:
        issues.append(
            {
                "kind": "policy",
                "severity": "error",
                "line": v.line,
                "message": v.detail,
                "fix_suggestion": "remove disallowed import or call",
            }
        )

    for m in detect_anti_patterns(code, registry=registry, package=package):
        issues.append(
            {
                "kind": "anti_pattern",
                "severity": m.severity,
                "line": m.line,
                "message": m.message,
                "anti_pattern_id": m.anti_pattern_id,
                "fix_suggestion": m.suggestion_idiom or "",
                "code_example_right": m.code_example_right,
            }
        )

    return success(
        "biobabel.check_code",
        summary=f"{len(issues)} issue(s)",
        outputs={"issues": issues, "code_safe": scan.ok},
    )


def match_failure(
    registry: Registry,
    *,
    error_text: str,
    package: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Map a runtime error/traceback the agent hit to curated failure fixes.

    The agent runs code with its own tools; when it raises, it passes the
    traceback here and biobabel returns the matching ``failure_fixes`` (and
    relevant anti-patterns) ranked by overlap. biobabel never executes anything —
    it only interprets the error the agent already produced.
    """
    if not error_text.strip():
        return error(
            "biobabel.match_failure",
            error_code="empty_error",
            message="error_text must be a non-empty traceback or error message",
        )

    matches = match_failures(registry, error_text, package=package, limit=limit)
    rows = [
        {
            "source": m.source,
            "package": m.package,
            "id": m.item_id,
            "when": m.when,
            "score": m.score,
            "suggest": m.suggest,
            "explanation": m.explanation,
            "correct_pattern": m.correct_pattern,
            "code_example_right": m.code_example_right,
        }
        for m in matches
    ]
    return success(
        "biobabel.match_failure",
        summary=f"{len(rows)} match(es) for the supplied error",
        outputs={"matches": rows},
    )
