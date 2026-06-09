"""Lexical search over contract objects.

This is deliberately unranked and deterministic.  The agent decides which
candidate is relevant to a user's task; biobabel only returns matching facts.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from biobabel._registry.builder import Registry

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]+")
_VALID_KINDS: frozenset[str] = frozenset(
    {"symbol", "workflow", "template", "concept", "idiom"}
)
_DEFAULT_KINDS: tuple[str, ...] = ("symbol", "workflow", "template", "concept", "idiom")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def search_contracts(
    registry: Registry,
    query: str,
    *,
    package: str | None = None,
    kinds: Iterable[str] = _DEFAULT_KINDS,
) -> list[dict[str, str]]:
    kinds_set = set(kinds)
    unknown = kinds_set - _VALID_KINDS
    if unknown:
        raise ValueError(
            f"unknown search kinds: {sorted(unknown)}; valid: {sorted(_VALID_KINDS)}"
        )
    q_toks = _tokens(query)
    if not q_toks:
        return []

    hits: list[dict[str, str]] = []
    for d in registry.packages.values():
        if package and d.import_name != package:
            continue
        m = d.manifest
        if "symbol" in kinds_set:
            for s in m.symbols:
                doc = " ".join(
                    [s.id, s.import_path, s.signature, s.purpose, s.description, *s.requires, *s.writes]
                )
                if _tokens(doc) & q_toks:
                    hits.append(_hit(d.import_name, "symbol", s.id, s.description or s.purpose))
        if "workflow" in kinds_set:
            for w in m.workflows:
                doc = " ".join(
                    [w.id, w.title, w.description, *w.task_tags, *w.when_to_use, *w.when_not_to_use]
                )
                if _tokens(doc) & q_toks:
                    hits.append(_hit(d.import_name, "workflow", w.id, w.description or w.title))
        if "template" in kinds_set:
            for t in m.templates:
                doc = " ".join([t.id, t.description, *t.task_tags, t.code_template])
                if _tokens(doc) & q_toks:
                    hits.append(_hit(d.import_name, "template", t.id, t.description))
        if "concept" in kinds_set:
            for c in m.concepts:
                doc = " ".join([c.id, c.name, c.category, c.description, c.mental_model, *c.invariants])
                if _tokens(doc) & q_toks:
                    hits.append(_hit(d.import_name, "concept", c.id, c.description))
        if "idiom" in kinds_set:
            for i in m.idioms:
                doc = " ".join([i.id, i.name, i.description, i.typical_use_case, i.code_template])
                if _tokens(doc) & q_toks:
                    hits.append(_hit(d.import_name, "idiom", i.id, i.description))

    hits.sort(key=lambda h: (h["package"], h["kind"], h["id"]))
    return hits


def _hit(package: str, kind: str, item_id: str, summary: str) -> dict[str, str]:
    return {
        "package": package,
        "kind": kind,
        "id": item_id,
        "summary": summary[:160],
    }
