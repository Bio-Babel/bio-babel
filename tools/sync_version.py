#!/usr/bin/env python
"""Stamp the single-source release version into the plugin/marketplace manifests.

The release version lives only in ``src/biobabel/__init__.py`` (``__version__``);
``pyproject.toml`` derives it dynamically. The plugin/marketplace JSON manifests
are read directly by Claude Code and Codex, so each must carry a literal string.
Bump ``__version__`` then run ``python tools/sync_version.py`` to propagate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src" / "biobabel" / "__init__.py"

TARGETS = [
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
    REPO_ROOT / "plugin" / "biobabel" / ".claude-plugin" / "plugin.json",
    REPO_ROOT / "plugin" / "biobabel-codex" / ".codex-plugin" / "plugin.json",
]

_VERSION_RE = re.compile(r'"version"(\s*:\s*)"[^"]*"')


def read_source_version() -> str:
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        SOURCE.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        sys.exit(f"ERROR: no __version__ found in {SOURCE}")
    return match.group(1)


def main() -> int:
    version = read_source_version()
    print(f"single source: {SOURCE.relative_to(REPO_ROOT)} → __version__ = {version}\n")

    changed = 0
    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        new_text = _VERSION_RE.sub(lambda m: f'"version"{m.group(1)}"{version}"', text)
        rel = path.relative_to(REPO_ROOT)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            n = len(_VERSION_RE.findall(text))
            print(f"  updated  {rel}  ({n} field{'' if n == 1 else 's'} → {version})")
            changed += 1
        else:
            print(f"  in sync  {rel}")

    print(f"\n{f'wrote {changed} file(s)' if changed else 'nothing to do — all in sync'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
