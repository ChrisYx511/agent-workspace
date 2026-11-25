# {{PROJECT}} agent workspace

Repository: {{REPOSITORY_URL}}
Trunk: `{{TRUNK}}` in [trunk/](trunk/). Shared Git store: `repository.git/`.

Start with [AGENTS.md](AGENTS.md), [TOC.md](TOC.md), and [DASHBOARD.html](DASHBOARD.html).
`workspace.json` holds the project name, repository URL, trunk, and dashboard timezone.
After changing dashboard settings, run `python3 workspace-status/update.py`.

Create a feature from the trunk worktree (replace `feature-name`):

```sh
cd trunk
git-spice log long
git-spice branch create feature-name --no-commit
git-spice branch checkout {{TRUNK}}
git worktree add ../feature-name feature-name
cd ../feature-name
```

Run the repository's setup commands inside the new worktree. Update the inventory
and create an owned progress record before implementation. Keep each feature stack
in one worktree. Use git-spice there to add increments and manage the stack.

For a local repository with no origin, add one before syncing or submitting.
Setup never pushes, installs tools, or runs repository-provided setup commands.
