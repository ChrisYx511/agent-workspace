"""Check setup with real Git stores, worktrees, and dashboard processes."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parents[1] / "setup.py"


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace with spaces"
        self.env = os.environ | {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }

    def run_command(self, *args, cwd=None, check=True):
        return subprocess.run(
            args, cwd=cwd, env=self.env, text=True, capture_output=True, check=check
        )

    def setup_workspace(self, *args, check=True):
        return self.run_command(
            sys.executable,
            str(SETUP),
            str(self.workspace),
            "--project",
            "Test <Project> & Team",
            "--trunk",
            "release/integration",
            "--timezone",
            "America/Toronto",
            *args,
            check=check,
        )

    def test_new_repository_dashboard_and_feature_worktree_lifecycle(self):
        self.setup_workspace("--new")
        trunk = self.workspace / "trunk"
        self.assertEqual(
            self.run_command(
                "git", "branch", "--show-current", cwd=trunk
            ).stdout.strip(),
            "release/integration",
        )
        self.assertEqual(
            self.run_command("git", "status", "--porcelain", cwd=trunk).stdout, ""
        )
        self.assertEqual(
            self.run_command(
                "git",
                f"--git-dir={self.workspace / 'repository.git'}",
                "rev-parse",
                "--is-bare-repository",
            ).stdout.strip(),
            "true",
        )
        dashboard = (self.workspace / "DASHBOARD.html").read_text()
        self.assertIn("Test &lt;Project&gt; &amp; Team", dashboard)
        self.assertIn("America/Toronto", dashboard)
        self.assertIn("No task records yet", dashboard)
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertTrue((self.workspace / name).is_symlink())
            self.assertEqual(
                (self.workspace / name).resolve(),
                (self.workspace / "NAVIGATE.md").resolve(),
            )
        self.assertNotIn("{{", ((self.workspace / "NAVIGATE.md").resolve()).read_text())
        feature = self.workspace / "feature"
        self.run_command(
            "git", "worktree", "add", "-b", "feature", str(feature), cwd=trunk
        )
        (feature / "example.txt").write_text("feature work\n")
        self.run_command("git", "add", "example.txt", cwd=feature)
        self.run_command("git", "commit", "-m", "Feature", cwd=feature)
        self.assertEqual(
            self.run_command("git", "status", "--porcelain", cwd=feature).stdout, ""
        )
        self.assertFalse((trunk / "example.txt").exists())
        self.run_command("git", "worktree", "remove", str(feature), cwd=trunk)

    def test_clone_selects_nondefault_trunk_and_can_fetch(self):
        source = self.root / "source"
        self.run_command("git", "init", "--initial-branch=main", str(source))
        (source / "README.md").write_text("Existing project\n")
        self.run_command("git", "add", ".", cwd=source)
        self.run_command("git", "commit", "-m", "Initial", cwd=source)
        self.run_command("git", "branch", "release/integration", cwd=source)
        self.setup_workspace(
            "--repo",
            str(source),
            "--repository-url",
            "https://example.com/team/project",
        )
        trunk = self.workspace / "trunk"
        self.assertEqual((trunk / "README.md").read_text(), "Existing project\n")
        self.assertEqual(
            self.run_command(
                "git", "branch", "--show-current", cwd=trunk
            ).stdout.strip(),
            "release/integration",
        )
        self.run_command("git", "fetch", "origin", cwd=trunk)
        self.assertEqual(
            self.run_command(
                "git", "rev-parse", "--abbrev-ref", "@{upstream}", cwd=trunk
            ).stdout.strip(),
            "origin/release/integration",
        )
        config = json.loads((self.workspace / "workspace.json").read_text())
        self.assertEqual(config["repository_url"], "https://example.com/team/project")
        self.assertIn(
            "https://example.com/team/project", (self.workspace / "TOC.md").read_text()
        )

    def test_git_spice_is_optional(self):
        executables = self.root / "bin"
        executables.mkdir()
        (executables / "git").symlink_to(shutil.which("git"))
        self.env["PATH"] = str(executables)
        result = self.setup_workspace("--new")
        self.assertIn("git-spice unavailable", result.stderr)
        self.assertTrue((self.workspace / "DASHBOARD.html").exists())
        self.assertEqual(
            self.run_command(
                "git", "status", "--porcelain", cwd=self.workspace / "trunk"
            ).stdout,
            "",
        )

    def test_existing_destination_is_unchanged(self):
        self.workspace.mkdir()
        sentinel = self.workspace / "keep.txt"
        sentinel.write_text("keep")
        self.assertNotEqual(self.setup_workspace("--new", check=False).returncode, 0)
        self.assertEqual(list(self.workspace.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_text(), "keep")

    def test_invalid_trunk_and_timezone_do_not_create_workspace(self):
        for args in (("--trunk", "bad branch"), ("--timezone", "Invalid/Zone")):
            with self.subTest(args=args):
                self.assertNotEqual(
                    self.setup_workspace("--new", *args, check=False).returncode, 0
                )
                self.assertFalse(self.workspace.exists())

    def test_new_repository_origin_is_configured_without_network(self):
        self.setup_workspace(
            "--new", "--remote-url", "https://example.invalid/team/project.git"
        )
        self.assertEqual(
            self.run_command(
                "git", "remote", "get-url", "origin", cwd=self.workspace / "trunk"
            ).stdout.strip(),
            "https://example.invalid/team/project.git",
        )

    def test_missing_clone_trunk_reports_failure_without_changing_source(self):
        source = self.root / "source"
        self.run_command("git", "init", "--initial-branch=main", str(source))
        self.run_command("git", "commit", "--allow-empty", "-m", "Initial", cwd=source)
        before = self.run_command("git", "show-ref", cwd=source).stdout
        self.assertNotEqual(
            self.setup_workspace("--repo", str(source), check=False).returncode, 0
        )
        self.assertEqual(self.run_command("git", "show-ref", cwd=source).stdout, before)


if __name__ == "__main__":
    unittest.main()
