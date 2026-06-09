"""Contract search is candidate retrieval, not planning."""

from __future__ import annotations

import pytest

from biobabel._registry.search import search_contracts


def test_search_contracts_returns_symbols(registry):
    hits = search_contracts(registry, "size factors")
    ids = {h["id"] for h in hits}
    assert "monocle3.estimate_size_factors" in ids


def test_search_contracts_returns_idioms(registry):
    hits = search_contracts(registry, "push draw pop")
    assert any(h["kind"] == "idiom" and h["id"] == "grid_py.push_draw_pop" for h in hits)


def test_search_contracts_can_filter_package(registry):
    hits = search_contracts(registry, "pseudotime", package="grid_py")
    assert hits == []


def test_search_contracts_is_sorted(registry):
    hits = search_contracts(registry, "viewport trajectory points")
    keys = [(h["package"], h["kind"], h["id"]) for h in hits]
    assert keys == sorted(keys)


def test_search_contracts_rejects_unknown_kind(registry):
    with pytest.raises(ValueError, match="unknown search kinds"):
        search_contracts(registry, "anything", kinds=["symbol", "bogus"])
