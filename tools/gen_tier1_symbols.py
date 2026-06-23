#!/usr/bin/env python
"""Tier-1 auto symbol-contract generator.

Emits the *automatic* API-surface layer — signature / parameters / types /
docstring — as SymbolContract YAML into ``<pkg>/_biobabel/symbols/``, reusing
biobabel's own retrofit introspection. It does NOT touch the hand-curated
tier-2 layer (idioms / templates / anti_patterns / concepts / workflows /
compositions stay intact); it only (re)writes ``symbols/*.yaml``.

Why a separate tool from ``retrofit_package``: retrofit scaffolds a WHOLE
``_biobabel/`` tree from scratch and refuses to run (or with --force, clobbers)
an existing one. The grammar packages (grid_py / gtable_py / scales) already
ship a curated ``_biobabel/`` but with ZERO symbol contracts — so an agent
asking "what are grid_xaxis's params" gets nothing. This tool fills only that
hole, idempotently, leaving every other curated file untouched.

These fields are machine-extracted from the *installed* package, so they are
fact, not claim — regenerate after a version bump. The semantic tier-2 fields
(failure_fixes, anti-patterns, produces/requires) are added per-symbol by hand
only where the python port diverges from the R / plotnine prior.

Usage:  python tools/gen_tier1_symbols.py grid_py gtable_py scales
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path

from biobabel._retrofit import retrofit as R

BANNER = (
    "# AUTO-GENERATED tier-1 API surface — signature/params/docstring introspected\n"
    "# from the installed package (fact, not claim). Regenerate after a version bump:\n"
    "#   python tools/gen_tier1_symbols.py <import_name>\n"
    "# Hand-curated tier-2 fields (failure_fixes / anti-patterns / produces) are added\n"
    "# directly in this file by humans and are NOT overwritten on regeneration unless\n"
    "# you delete the file first.\n"
)


def generate(import_name: str) -> int:
    spec = importlib.util.find_spec(import_name)
    if spec is None or spec.origin is None:
        raise SystemExit(f"cannot locate package '{import_name}'")
    root = Path(spec.origin).parent.resolve()
    symbols, warns, skipped = R._introspect_robust(import_name, root)

    # Recover real public API the package forgot to put in __all__: top-level
    # function/class objects DEFINED in this package (e.g. grid_py.CairoRenderer
    # lives in grid_py.renderer and is importable, but is missing from __all__).
    # Restrict to own-package function/class so external re-exports (numpy, ...),
    # submodules, and module-level constants are NOT pulled in.
    have = {s.name for s in symbols}
    recovered = 0
    try:
        mod = importlib.import_module(import_name)
    except Exception:
        mod = None  # C-ext unavailable: keep the AST-fallback symbols only
    if mod is not None:
        for name in dir(mod):
            if name.startswith("_") or name in have:
                continue
            obj = getattr(mod, name, None)
            objmod = getattr(obj, "__module__", "") or ""
            if objmod.startswith(import_name) and (
                inspect.isfunction(obj) or inspect.isclass(obj) or inspect.isbuiltin(obj)
            ):
                symbols.append(R._describe(name, obj, import_name))
                recovered += 1

    public = [s for s in symbols if s.name and not s.name.startswith("_")]
    symdir = root / "_biobabel" / "symbols"
    symdir.mkdir(parents=True, exist_ok=True)
    written = protected = 0
    for s in public:
        target = symdir / f"{s.name}.yaml"
        # Never clobber a human-curated tier-2 file: only (re)write files that
        # are absent or that we generated ourselves (marked by the banner).
        if target.exists() and not target.read_text(encoding="utf-8").lstrip().startswith(
            "# AUTO-GENERATED tier-1"
        ):
            protected += 1
            continue
        target.write_text(BANNER + R._render_symbol_yaml(s, import_name), encoding="utf-8")
        written += 1
    print(f"{import_name:12} {written:4} written, {protected:4} human-curated kept "
          f"(+{recovered} recovered from missing __all__) -> {symdir}")
    return written


if __name__ == "__main__":
    pkgs = sys.argv[1:] or ["grid_py", "gtable_py", "scales"]
    total = sum(generate(p) for p in pkgs)
    print(f"total: {total} tier-1 symbol contracts")
