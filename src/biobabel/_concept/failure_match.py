"""Match a runtime error / traceback to curated failure knowledge.

The agent runs code with its OWN tools; when that code raises, the highest-signal
correctness feedback in the whole loop is the traceback. biobabel never executes
anything, but it *can* interpret that traceback: this module lexically matches the
error text against every symbol's ``failure_fixes`` (which producers author keyed
by error condition) and against anti-pattern ``why_bad`` text, returning the
curated fix.

This closes the one delivery gap in the read-only layer: ``failure_fixes`` are
authored by *error condition* but were previously only reachable by *symbol*
(``describe_symbol``), so an agent holding nothing but a traceback could not get
to them. It is the literal "agent executes, biobabel interprets" path.

Matching is deliberately lexical and deterministic (token overlap), mirroring
``_registry/search.py``: biobabel returns scored candidates and the agent decides.
Generic boilerplate tokens can produce low-score noise; that is acceptable at v1
and is exactly what the ``score`` field lets the agent rank away.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from biobabel._registry.builder import Registry

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


@dataclass(frozen=True)
class FailureMatch:
    """One curated fix whose authored condition overlaps the supplied error."""

    source: str  # "failure_fix" | "anti_pattern"
    package: str
    item_id: str  # symbol id (failure_fix) or anti-pattern id
    when: str  # the matched condition text
    score: int
    suggest: list[str] = field(default_factory=list)
    explanation: str = ""
    correct_pattern: str = ""
    code_example_right: str = ""


def match_failures(
    registry: Registry,
    error_text: str,
    *,
    package: str | None = None,
    limit: int = 5,
) -> list[FailureMatch]:
    """Return curated fixes whose authored condition overlaps *error_text*.

    Candidates come from two sources:

    - ``SymbolContract.failure_fixes`` — matched on the fix's ``when`` plus the
      symbol id/import_path (a traceback names the failing callable, so the id is
      high signal).
    - ``AntiPatternSpec`` — matched on ``why_bad`` / ``name`` / id.

    Ranked by descending token-overlap score, then package, then id. Returns at
    most *limit* matches; an empty or token-less ``error_text`` yields ``[]``.
    """
    err = _tokens(error_text)
    if not err:
        return []

    matches: list[FailureMatch] = []

    for pkg, symbol in registry.list_symbols(package=package):
        symbol_tokens = _tokens(f"{symbol.id} {symbol.import_path}")
        for ff in symbol.failure_fixes:
            score = len(err & (_tokens(ff.when) | symbol_tokens))
            if score:
                matches.append(
                    FailureMatch(
                        source="failure_fix",
                        package=pkg,
                        item_id=symbol.id,
                        when=ff.when,
                        score=score,
                        suggest=list(ff.suggest),
                        explanation=ff.explanation,
                    )
                )

    for pkg, spec in registry.all_anti_patterns():
        if package and pkg != package:
            continue
        score = len(err & _tokens(f"{spec.why_bad} {spec.name} {spec.id}"))
        if score:
            matches.append(
                FailureMatch(
                    source="anti_pattern",
                    package=pkg,
                    item_id=spec.id,
                    when=spec.why_bad or spec.name,
                    score=score,
                    correct_pattern=spec.correct_pattern or "",
                    code_example_right=spec.code_example_right,
                )
            )

    matches.sort(key=lambda m: (-m.score, m.package, m.item_id))
    return matches[: max(1, limit)]
