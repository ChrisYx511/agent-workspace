# Agent workspace template

Create a workspace with a shared bare Git store, one worktree per feature stack,
a trunk checkout, a stack inventory, and an agent-maintained progress dashboard.
The source template contains no application code, PR history, or live task records.

Requires Python 3.12+, Git, and macOS/Linux. Install git-spice separately for stack
management. Setup initializes it when the `git-spice` executable is available.
No dependencies are installed and no branches are pushed.

Clone an existing repository. The selected trunk must already exist; it can differ
from the repository's default branch:

```sh
python3 setup.py ../my-project-workspace \
  --repo git@github.com:team/my-project.git \
  --repository-url https://github.com/team/my-project \
  --project 'My Project' --trunk develop --timezone America/Toronto
```

Create a new local repository with a trunk of your choice:

```sh
python3 setup.py ../new-project-workspace \
  --new --project 'New Project' --trunk integration
```

Optionally add `--remote-url git@github.com:team/new-project.git` to configure
origin. This does not create a hosted repository or push the initial commit.
New repositories get one empty initial commit, authored by `Workspace Setup`,
so worktrees and branches work immediately. Normal commits use your Git identity.

The destination must not exist. On failure, partial files stay available for
inspection. Setup does not delete them or overwrite an existing workspace.
Clone URLs can be local paths, HTTPS, or SSH URLs. Use credential helpers rather
than embedding credentials in URLs; the display URL is saved in workspace metadata.

```text
my-project-workspace/
  AGENTS.md -> NAVIGATE.md
  CLAUDE.md -> NAVIGATE.md
  NAVIGATE.md              Agent workflow and worktree lifecycle
  TOC.md                   Feature stack inventory and dependency status
  STACK-MIGRATION.md       Optional pending work / frozen boundary rules
  DASHBOARD.html           Generated local progress dashboard
  workspace.json           Project name, URL, trunk, dashboard timezone
  repository.git/          Shared bare Git store
  trunk/                   The only worktree checking out trunk
  skills/                  Portable workflow instructions
  workspace-status/        Updater, example record, tests, owned task records
  feature-name/            Added when a feature starts; one folder per stack
```

Setup substitutes `{{PROJECT}}`, `{{REPOSITORY_URL}}`, `{{TRUNK}}`, `{{WORKSPACE}}`,
and `{{DATE}}` in the navigation documents. The dashboard reads `workspace.json`
for its project name and timezone on every regeneration. HTML output escapes the
project name. Repository files and repository-owned `AGENTS.md` are left intact.

Keep the template directory for reuse; run setup again with a different destination.
The generated workspace has its own README and commands for starting a feature.
Run each repository's setup commands inside each new worktree. Share Git and
stack metadata operations one at a time even when feature work runs in parallel.
Keep each worktree until its stack has no branches and no uncommitted work remains.

Test the template with real temporary Git repositories:

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s template/workspace-status -v
```
