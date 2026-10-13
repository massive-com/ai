#!/usr/bin/env python3
"""Check that the marketplace catalogs agree with the plugins on disk.

`claude plugin validate .` checks the Claude catalog's schema and that each
source path resolves. This checks what it cannot:

- Every plugin directory is listed in the Claude catalog.
- Each plugin's directory name equals its `name`.
- The catalog versions match the plugin manifests. Claude Code only picks up a
  change when the version changes, so a stale version ships stale content.
- The Cursor catalog points at plugins that have a Cursor manifest, at the same
  version as their Claude manifest.

Run it from the repo root: `python3 scripts/check_catalog.py`. Standard library
only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_CATALOG = ".claude-plugin/marketplace.json"
CURSOR_CATALOG = ".cursor-plugin/marketplace.json"
PLUGINS_DIR = "providers/claude/plugins"


def load(path: str, errors: list[str]) -> dict | None:
    try:
        return json.loads((ROOT / path).read_text())
    except FileNotFoundError:
        errors.append(f"{path}: file is missing")
    except json.JSONDecodeError as e:
        errors.append(f"{path}: invalid JSON ({e})")
    return None


def source_dir(source: str) -> str:
    return source.removeprefix("./").rstrip("/")


def check() -> list[str]:
    errors: list[str] = []

    claude = load(CLAUDE_CATALOG, errors)
    if claude is None:
        return errors

    listed = set()
    for entry in claude.get("plugins", []):
        name, source = entry.get("name"), entry.get("source")
        if not isinstance(source, str):
            continue  # a remote source: nothing on disk to compare
        directory = source_dir(source)
        listed.add(directory)
        where = f"{CLAUDE_CATALOG}: plugin {name!r}"

        if Path(directory).name != name:
            errors.append(f"{where}: directory {directory} must match the plugin name")
        manifest_path = f"{directory}/.claude-plugin/plugin.json"
        manifest = load(manifest_path, errors)
        if manifest is None:
            continue
        if manifest.get("name") != name:
            errors.append(f"{where}: {manifest_path} has name {manifest.get('name')!r}")
        if manifest.get("version") != entry.get("version"):
            errors.append(
                f"{where}: version {entry.get('version')!r} differs from "
                f"{manifest_path} ({manifest.get('version')!r})"
            )

    plugins_root = ROOT / PLUGINS_DIR
    if plugins_root.is_dir():
        for child in sorted(plugins_root.iterdir()):
            if child.is_dir() and f"{PLUGINS_DIR}/{child.name}" not in listed:
                errors.append(f"{PLUGINS_DIR}/{child.name} is on disk but not listed in {CLAUDE_CATALOG}")

    cursor = load(CURSOR_CATALOG, errors) if (ROOT / CURSOR_CATALOG).exists() else None
    for entry in (cursor or {}).get("plugins", []):
        name, directory = entry.get("name"), source_dir(entry.get("source", ""))
        where = f"{CURSOR_CATALOG}: plugin {name!r}"
        cursor_manifest = load(f"{directory}/.cursor-plugin/plugin.json", errors)
        claude_manifest = load(f"{directory}/.claude-plugin/plugin.json", errors)
        if cursor_manifest is None or claude_manifest is None:
            continue
        versions = {
            CURSOR_CATALOG: entry.get("version"),
            f"{directory}/.cursor-plugin/plugin.json": cursor_manifest.get("version"),
            f"{directory}/.claude-plugin/plugin.json": claude_manifest.get("version"),
        }
        if len(set(versions.values())) > 1:
            found = ", ".join(f"{path}={version!r}" for path, version in versions.items())
            errors.append(f"{where}: versions differ ({found})")

    return errors


def main() -> int:
    # Both catalogs load a shared manifest, so a broken one is reported twice.
    errors = list(dict.fromkeys(check()))
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Catalogs agree with the plugins on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
