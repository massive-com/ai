"""Tests for the MCP-file and version-bump checks in check_catalog.py.

Each test builds a small repo with one plugin "pub", breaks one thing, and
asserts the error. Run with `python3 -m unittest discover -s scripts -p 'test_*.py'`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_catalog as cc  # noqa: E402

PLUGIN = Path(cc.PLUGINS_DIR) / "pub"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def mcp(url: str) -> dict:
    return {"mcpServers": {"pub": {"url": url}}}


class PluginTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.addCleanup(setattr, cc, "ROOT", cc.ROOT)
        cc.ROOT = self.repo
        write_json(self.repo / PLUGIN / ".claude-plugin/plugin.json", {"name": "pub", "version": "0.1.0"})
        (self.repo / PLUGIN / "skills").mkdir(parents=True)
        (self.repo / PLUGIN / "skills/SKILL.md").write_text("v1\n")


class McpFilesTest(PluginTestCase):
    def test_no_mcp_files_passes(self) -> None:
        self.assertEqual(cc.check_mcp_files(), [])

    def test_matching_urls_pass(self) -> None:
        write_json(self.repo / PLUGIN / ".mcp.json", mcp("https://a.example"))
        write_json(self.repo / PLUGIN / "mcp.json", mcp("https://a.example"))
        self.assertEqual(cc.check_mcp_files(), [])

    def test_different_urls_fail(self) -> None:
        write_json(self.repo / PLUGIN / ".mcp.json", mcp("https://a.example"))
        write_json(self.repo / PLUGIN / "mcp.json", mcp("https://b.example"))
        [error] = cc.check_mcp_files()
        self.assertIn("differ from mcp.json", error)

    def test_one_file_alone_fails(self) -> None:
        write_json(self.repo / PLUGIN / ".mcp.json", mcp("https://a.example"))
        [error] = cc.check_mcp_files()
        self.assertIn("has .mcp.json but no mcp.json", error)


class VersionBumpTest(PluginTestCase):
    def setUp(self) -> None:
        super().setUp()
        for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                     ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base"]):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True)
        (self.repo / PLUGIN / "skills/SKILL.md").write_text("v2\n")

    def commit(self) -> None:
        subprocess.run(["git", "-C", str(self.repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "-m", "change"], check=True)

    def test_change_without_bump_fails(self) -> None:
        self.commit()
        [error] = cc.check_versions_bumped("HEAD~1")
        self.assertIn("version is still '0.1.0'", error)

    def test_change_with_bump_passes(self) -> None:
        write_json(self.repo / PLUGIN / ".claude-plugin/plugin.json", {"name": "pub", "version": "0.1.1"})
        self.commit()
        self.assertEqual(cc.check_versions_bumped("HEAD~1"), [])

    def test_bump_that_matches_a_newer_base_fails(self) -> None:
        # The PR bumps to 0.1.1, but the base branch already moved to 0.1.1.
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "branch", "base"], check=True)
        write_json(self.repo / PLUGIN / ".claude-plugin/plugin.json", {"name": "pub", "version": "0.1.1"})
        self.commit()
        subprocess.run([*git, "checkout", "-q", "base"], check=True)
        (self.repo / PLUGIN / "skills/SKILL.md").write_text("v3\n")
        write_json(self.repo / PLUGIN / ".claude-plugin/plugin.json", {"name": "pub", "version": "0.1.1"})
        self.commit()
        subprocess.run([*git, "checkout", "-q", "main"], check=True)
        [error] = cc.check_versions_bumped("base")
        self.assertIn("version is still '0.1.1'", error)

    def test_no_bump_when_base_moved_on_fails(self) -> None:
        # The base branch bumps to 0.1.1. The PR changes a skill and keeps 0.1.0.
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "branch", "base"], check=True)
        self.commit()
        subprocess.run([*git, "checkout", "-q", "base"], check=True)
        write_json(self.repo / PLUGIN / ".claude-plugin/plugin.json", {"name": "pub", "version": "0.1.1"})
        self.commit()
        subprocess.run([*git, "checkout", "-q", "main"], check=True)
        [error] = cc.check_versions_bumped("base")
        self.assertIn("version is still '0.1.0'", error)

    def test_invalid_manifest_reports_the_file(self) -> None:
        (self.repo / PLUGIN / ".claude-plugin/plugin.json").write_text("{not json")
        self.commit()
        [error] = cc.check_versions_bumped("HEAD~1")
        self.assertIn("plugin.json: invalid JSON", error)

    def test_bad_ref_reports_git_error(self) -> None:
        [error] = cc.check_versions_bumped("no-such-ref")
        self.assertIn("git diff against 'no-such-ref' failed", error)


if __name__ == "__main__":
    unittest.main()
