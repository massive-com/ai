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
- A plugin's `.mcp.json` (Claude Code) and `mcp.json` (Cursor) register the
  same servers at the same URLs.
- With `--base <ref>`: a plugin with changes since `<ref>` has a new version.

Run it from the repo root: `python3 scripts/check_catalog.py`. On a pull
request, add `--base origin/<base branch>`. Standard library only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_CATALOG = ".claude-plugin/marketplace.json"
CURSOR_CATALOG = ".cursor-plugin/marketplace.json"
PLUGINS_DIR = "providers/claude/plugins"
MCP_FILES = (".mcp.json", "mcp.json")


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

    for child in plugin_dirs():
        if f"{PLUGINS_DIR}/{child.name}" not in listed:
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


def plugin_dirs() -> list[Path]:
    plugins_root = ROOT / PLUGINS_DIR
    if not plugins_root.is_dir():
        return []
    return sorted(child for child in plugins_root.iterdir() if child.is_dir())


def server_urls(path: str, errors: list[str]) -> dict[str, str] | None:
    config = load(path, errors)
    if config is None:
        return None
    return {name: server.get("url") for name, server in config.get("mcpServers", {}).items()}


def check_mcp_files() -> list[str]:
    """Each plugin has both MCP files or neither, and both register the same URLs."""
    errors: list[str] = []
    for child in plugin_dirs():
        directory = f"{PLUGINS_DIR}/{child.name}"
        present = [name for name in MCP_FILES if (child / name).exists()]
        if len(present) == 1:
            errors.append(f"{directory}: has {present[0]} but no {(set(MCP_FILES) - set(present)).pop()}")
        if len(present) != 2:
            continue
        claude_code, cursor = (server_urls(f"{directory}/{name}", errors) for name in MCP_FILES)
        if claude_code is not None and cursor is not None and claude_code != cursor:
            errors.append(f"{directory}: .mcp.json servers {claude_code} differ from mcp.json servers {cursor}")
    return errors


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def version_at(ref: str, manifest_path: str) -> str | None:
    """The plugin version at `ref`, or None when the manifest is missing or invalid there."""
    shown = git("show", f"{ref}:./{manifest_path}")
    if shown.returncode != 0:
        return None
    try:
        return json.loads(shown.stdout).get("version")
    except json.JSONDecodeError:
        return None


def check_versions_bumped(base: str) -> list[str]:
    """A plugin with changes since `base` has a version that differs from the earlier version.

    Claude Code ignores a plugin change when the version stays the same. The
    check compares with the merge-base and with the `base` tip. The merge-base
    catches a missing bump when `base` moved on. The tip catches two PRs that
    bump to the same version.
    """
    diff = git("diff", "--name-only", "--relative", f"{base}...HEAD", "--", PLUGINS_DIR)
    if diff.returncode != 0:
        return [f"git diff against {base!r} failed: {diff.stderr.strip()}"]
    merge_base = git("merge-base", base, "HEAD")
    if merge_base.returncode != 0:
        return [f"git merge-base {base!r} HEAD failed: {merge_base.stderr.strip()}"]
    changed = {Path(line).parts[3] for line in diff.stdout.splitlines() if len(Path(line).parts) > 4}

    errors: list[str] = []
    for name in sorted(changed):
        manifest_path = f"{PLUGINS_DIR}/{name}/.claude-plugin/plugin.json"
        if not (ROOT / manifest_path).exists():
            continue  # a deleted plugin
        manifest = load(manifest_path, errors)
        if manifest is None:
            continue
        new = manifest.get("version")
        earlier = {version_at(ref, manifest_path) for ref in (merge_base.stdout.strip(), base)} - {None}
        if new in earlier:
            errors.append(f"{PLUGINS_DIR}/{name} changed since {base} but its version is still {new!r}. Bump it.")
    return errors


def main() -> int:
    args = sys.argv[1:]
    if args and not (len(args) == 2 and args[0] == "--base"):
        print("usage: check_catalog.py [--base <ref>]", file=sys.stderr)
        return 2
    results = check() + check_mcp_files()
    if args:
        results += check_versions_bumped(args[1])
    # Both catalogs load a shared manifest, so a broken one is reported twice.
    errors = list(dict.fromkeys(results))
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Catalogs agree with the plugins on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
