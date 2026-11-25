#!/usr/bin/env python3
"""Create an agent workspace in a new directory (Python 3.12+, macOS/Linux)."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def run(*args, cwd=None, input=None):
    return subprocess.run(
        args, cwd=cwd, input=input, text=True, check=True, capture_output=True
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", type=Path, help="new workspace directory; must not exist"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--repo", help="existing repository URL or local path to bare-clone"
    )
    mode.add_argument("--new", action="store_true", help="create a new repository")
    parser.add_argument("--project", required=True, help="project display name")
    parser.add_argument(
        "--trunk", required=True, help="trunk branch, independent of remote HEAD"
    )
    parser.add_argument(
        "--remote-url", help="origin URL for --new; no remote repository is created"
    )
    parser.add_argument(
        "--repository-url", help="display/link URL, if different from the clone URL"
    )
    parser.add_argument(
        "--timezone", default="UTC", help="IANA dashboard timezone (default: UTC)"
    )
    args = parser.parse_args()
    workspace = args.directory.expanduser().resolve()
    if workspace.exists():
        parser.error("workspace directory already exists; nothing was changed")
    if args.remote_url and not args.new:
        parser.error("--remote-url requires --new")
    if not args.project.strip() or any(c in args.project for c in "\n\r"):
        parser.error("--project must be a nonempty single line")
    ZoneInfo(args.timezone)
    run("git", "check-ref-format", "--branch", args.trunk)
    if args.trunk.startswith("-") or args.trunk == "HEAD":
        parser.error("invalid trunk branch")
    repository_url = (
        args.repository_url
        or args.repo
        or args.remote_url
        or "Local repository (no origin)"
    )
    if any(c in repository_url for c in "\n\r"):
        parser.error("repository URL must be a single line")
    config = {
        "project": args.project,
        "repository_url": repository_url,
        "trunk": args.trunk,
        "timezone": args.timezone,
    }
    # Reserve the directory before copying; never merge into an existing workspace.
    workspace.mkdir(parents=True)
    shutil.copytree(
        Path(__file__).resolve().parent / "template",
        workspace,
        dirs_exist_ok=True,
        symlinks=True,
        ignore=shutil.ignore_patterns("__pycache__", ".update.lock"),
    )
    (workspace / "workspace.json").write_text(json.dumps(config, indent=2) + "\n")
    values = {
        "PROJECT": args.project,
        "WORKSPACE": str(workspace),
        "REPOSITORY_URL": repository_url,
        "TRUNK": args.trunk,
        "DATE": datetime.now(ZoneInfo(args.timezone)).date().isoformat(),
    }
    for name in ("README.md", "NAVIGATE.md", "TOC.md", "STACK-MIGRATION.md"):
        path = workspace / name
        content = path.read_text()
        # Replace tokens in one pass so inserted values are never treated as templates.
        content = re.sub(r"\{\{([A-Z_]+)\}\}", lambda match: values[match[1]], content)
        path.write_text(content)
    bare = workspace / "repository.git"
    if args.repo:
        run("git", "clone", "--bare", "--", args.repo, str(bare))
        run(
            "git",
            f"--git-dir={bare}",
            "show-ref",
            "--verify",
            f"refs/heads/{args.trunk}",
        )
    else:
        run("git", "init", "--bare", f"--initial-branch={args.trunk}", str(bare))
        # A real initial commit lets worktrees and feature branches start immediately.
        tree = run(
            "git",
            f"--git-dir={bare}",
            "hash-object",
            "-t",
            "tree",
            "-w",
            "--stdin",
            input="",
        )
        commit = run(
            "git",
            f"--git-dir={bare}",
            "-c",
            "user.name=Workspace Setup",
            "-c",
            "user.email=workspace@localhost",
            "commit-tree",
            tree,
            "-m",
            "Initial commit",
        )
        run(
            "git", f"--git-dir={bare}", "update-ref", f"refs/heads/{args.trunk}", commit
        )
        if args.remote_url:
            run("git", f"--git-dir={bare}", "remote", "add", "origin", args.remote_url)
    run("git", f"--git-dir={bare}", "symbolic-ref", "HEAD", f"refs/heads/{args.trunk}")
    if args.repo or args.remote_url:
        # Bare clones omit remote-tracking refs; sync needs an ordinary origin refspec.
        run(
            "git",
            f"--git-dir={bare}",
            "config",
            "remote.origin.fetch",
            "+refs/heads/*:refs/remotes/origin/*",
        )
        if args.repo:
            run("git", f"--git-dir={bare}", "fetch", "origin")
            run(
                "git",
                f"--git-dir={bare}",
                "config",
                f"branch.{args.trunk}.remote",
                "origin",
            )
            run(
                "git",
                f"--git-dir={bare}",
                "config",
                f"branch.{args.trunk}.merge",
                f"refs/heads/{args.trunk}",
            )
    run("git", f"--git-dir={bare}", "config", "extensions.worktreeConfig", "true")
    # Keep bare=true local to the Git store, so linked worktrees work normally.
    run("git", f"--git-dir={bare}", "config", "--worktree", "core.bare", "true")
    run("git", f"--git-dir={bare}", "config", "--unset", "core.bare")
    run(
        "git",
        f"--git-dir={bare}",
        "worktree",
        "add",
        str(workspace / "trunk"),
        args.trunk,
    )
    if shutil.which("git-spice"):
        run(
            "git-spice",
            "--no-prompt",
            "repo",
            "init",
            "--trunk",
            args.trunk,
            "--remote",
            "origin",
            cwd=workspace / "trunk",
        )
        run("git-spice", "log", "long", cwd=workspace / "trunk")
    else:
        print(
            "git-spice unavailable; use Git until it is installed and initialized.",
            file=sys.stderr,
        )
    run(sys.executable, str(workspace / "workspace-status/update.py"))
    print(f"Workspace ready: {workspace}\nStart with AGENTS.md and DASHBOARD.html.")


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        OSError,
        ZoneInfoNotFoundError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        print(
            "If a directory was created, inspect it before removing it and retrying. No remote changes were made.",
            file=sys.stderr,
        )
        sys.exit(1)
