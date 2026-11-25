# {{PROJECT}} Working Directories Tree

How to navigate:

- Each feature folder in this root represents one PR stack (a feature) off of the {{TRUNK}} trunk branch, each containing one worktree checking out a branch on a git-spice stack
- The entire stack of PRs should be managed as a single worktree, in its folder
- When starting work on a new feature off of {{TRUNK}}, create a new worktree in a new folder, and manage the stack using git-spice in that folder
- When work is complete on a stack and there are no longer any branches on the stack, delete the entire worktree
- When a PR is merged, delete the branch from the stack and continue working on the remaining branches in the stack, do not remove the worktree
- The trunk branch is checked out in `trunk`, and should not be checked out anywhere else, as it is the source of truth for the entire stack of PRs
- Manage all restacking, submissions, and merges using git-spice in the worktree folder
- The git metadata folder is also in the root

P.S. REMEMBER: the repository’s documented setup command and any other project setup commands should be run in the worktree folder, not in the root of the repo and must be rerun for each new worktree created. This ensures that the environment is correctly configured for the specific feature being developed.

Use the relevant skills for navigating PR stacks and writing code effectively.

Read this workspace navigation first. Before work inside a repository worktree, read its `AGENTS.md` and `CLAUDE.md` files, when present, and any nested instructions that apply to the files being changed. Follow both the workspace workflow and the repository-specific instructions. Leave repository-owned instruction files intact.

## Workspace progress dashboard

Read [DASHBOARD.html](./DASHBOARD.html) at task start. Keep this dashboard current for work in any worktree, including work in the workspace root. This is an agent work log; `TOC.md` remains the stack inventory and follows its existing update rules.

- Before starting or resuming work, create or update a task record through [workspace-status/update.py](./workspace-status/update.py). Follow [the record format and commands](./workspace-status/README.md). Record the feature, work order, owning agent, worktree, prerequisites/PR order, current step, completed and remaining steps, blockers, next action, and check evidence.
- Give each independently owned task a stable, unique task ID and owner label. Parallel agents must use different records, even within the same feature. Update only your record. An `unassigned` seed may be claimed after verifying its state; an old timestamp alone does not authorize taking over another agent's work.
- Update at task start, on scope changes, after meaningful milestones, when blockers change, and before handoff or the final answer. During sustained work, refresh at least every ten minutes when control returns between operations. Do not interrupt checks or change another agent's work to meet this interval.
- Submit a complete JSON record from a temporary file outside `workspace-status/items/`: `python3 {{WORKSPACE}}/workspace-status/update.py TASK_ID < /tmp/task-status.json`. The script records the current timestamp, protects ownership, serializes concurrent updates, and atomically regenerates `DASHBOARD.html`. Do not edit generated HTML or saved record files directly.
- State actual progress and uncertainty. Count completed outcomes, not effort or guessed percentages. Keep deferred work visible but outside the active remainder. Never describe old checks as validation of a new revision or mark an interrupted task complete.
- Keep completed records as history. For a handoff, record the next action and actual remaining work. If work stops and the resume state is uncertain, use `needs_update`; use `blocked` only for an identified blocker and `backlog` for deliberately deferred work. No background monitor updates this dashboard when agents are idle.
- Do not copy design documents into status records. Keep concise progress/evidence here and link design material in the project’s document system. Do not put secrets, credentials, or private source data in status records.

## Stack index and status metadata

Read [TOC.md](./TOC.md) before working on a stack. For pending work, also read [STACK-MIGRATION.md](./STACK-MIGRATION.md). The TOC is a dated navigation snapshot. Verify the current branch graph and PR state before acting on it.

- Keep stack descriptions and status metadata in `TOC.md`. Do not copy these blocks into PR descriptions or comments. Preserve existing PR descriptions when updating status labels.
- Update the affected TOC entries when creating, splitting, reorganizing, activating, deferring, or removing a stack, or when the user requests an update. Routine merges do not require a TOC update each time. Record the update date and preserve unrelated entries.
- Link every worktree and each PR's base. Each stack description must include its purpose, status, PR membership, current worktree, prerequisites, and next step or resume condition.
- Use **Active** for a stack available for work or review. Use **Blocked** when prerequisites or a frozen boundary prevent progress. Use **Backlog** when work is deliberately deferred by priority. Internal PR order still applies within an Active stack.
- Identify future feature groups as **planned stacks** until they are extracted. Show their actual current worktree. Do not imply that groups sharing `pending-features` already have independent branches or worktrees.
- If GitHub is used, apply the repository’s `blocked` label to every PR in a Blocked group. Preserve other labels. Remove `blocked` only from a subset whose blockers have been resolved and whose extraction has been verified. A Backlog status alone does not imply a dependency blocker.
- Keep held PRs as drafts. A label alone does not prevent merging. Removing a label does not by itself make a PR ready for review or merge.
- For label-only updates, use a metadata-only operation, such as the GitHub labels API through `gh`. Do not push branches or resubmit a stack just to change labels. Verify the resulting labels and preserve PR descriptions, draft states, heads, and bases unless the task also calls for changing them.
- After a TOC update, verify local links, PR membership, base links, and status consistency. Each pending PR must belong to exactly one planned feature group.

## Pending feature workflow

Read the selected group's metadata in [TOC.md](./TOC.md) and the frozen-base rules in [STACK-MIGRATION.md](./STACK-MIGRATION.md). Frozen branches preserve old prerequisite commits. Keep their exact commits fixed until their boundaries are reconciled. Do not create PRs for them, merge them into {{TRUNK}}, or merge pending PRs into them.

### Promote a pending group into an active feature stack

An active feature stack must contain a working feature on its intended base. Its root must start from the synced {{TRUNK}} branch. It must not require unmerged work from another stack or retain a frozen migration base. Its own PRs may depend on earlier PRs in that stack.

1. Inspect `git-spice log long` in `pending-features`. Identify the exact PRs to extract, their prerequisites, and any remaining descendants that depend on them. Record the current heads, bases, and frozen commits for recovery. Preserve uncommitted work before changing history.
2. Sync {{TRUNK}} using the workflow below. Confirm the required feature work is present in {{TRUNK}}. A merged prerequisite does not release every group or every PR in that group. Release a smaller verified subset when only part of a group is ready.
3. Plan the extraction before moving branches. If the selected root and its entire upstack contain only the chosen feature, use `git-spice upstack onto {{TRUNK}} --branch FEATURE_ROOT_BRANCH` from the owning worktree. Replace the placeholder with the real branch name. Do not use this command when it would carry unrelated pending PRs or frozen branches into the new stack.
4. For interleaved PRs or shared prerequisites, first plan how the remaining pending branches will retain their required history. Check installed CLI help before using scoped moves. `git-spice branch onto` moves one branch but also retargets its former children; it is not a safe shortcut without checking those children. Preserve existing PR identities and verify each affected immediate-parent diff. Do not routinely restack across a frozen descendant. Reconcile that boundary first under the migration guide.
5. Once the feature is isolated, give it a named worktree in this workspace using the existing shared Git store. If its branch is still checked out in `pending-features`, first use git-spice to check out a surviving pending branch there. From that folder, `git worktree add ../FEATURE_DIRECTORY FEATURE_TIP_BRANCH` creates the new worktree. Replace both placeholders. Run the repository’s documented setup command inside the new folder. Never check out {{TRUNK}} there.
6. In the new worktree, inspect the stack and run `git-spice stack restack`. Resolve conflicts without dropping behavior, validation, or tests. Run the required checks on the resulting revisions. When submission is authorized, use `git-spice stack submit --update-only` for the existing PRs. Verify remote heads, bases, and PR order. Check that the remaining pending groups still have their required history and unchanged frozen commits.
7. Update the TOC with the new worktree, PR order, bases, and Active status. Remove `blocked` only from the released PRs. Keep other groups Blocked. Do not mark drafts ready for review unless that is part of the task. Retire a frozen alias only after its required work is available and no remaining descendant needs it. Preserve deferred branches and keep worktrees that still own branches.

Keep the pending worktree's `spice.submit.updateOnly=true` guard. Use explicit `--update-only` for pending submissions. These guards do not replace checking for frozen-branch pushes or unintended changes.

## Sync {{TRUNK}} and restack the worktrees

Perform this workflow when asked to bring the workspace stacks onto the latest {{TRUNK}}. Process shared Git and git-spice changes one worktree at a time.

1. Inspect the live worktree list, branch graph, and worktree status. Preserve uncommitted work. If a merged PR branch is checked out in another worktree, use git-spice there to switch to a surviving branch in that stack. If the whole stack has merged, use `git-spice branch checkout --detach MERGED_BRANCH` to release its branch before sync. Do not check out {{TRUNK}} in that worktree.
2. Go to `trunk` and sync once:

   ```sh
   cd "{{WORKSPACE}}/trunk"
   git-spice log long --all
   git-spice repo sync --restack=none
   ```

   Sync updates the shared trunk. It can also delete merged PR branches and retarget descendants. The explicit `--restack=none` leaves rebasing to the individual worktrees. Inspect the resulting graph before continuing. Do not run `git-spice repo restack` or a whole-workspace submission from `trunk`.

3. Visit each active feature worktree. Confirm its surviving root is based on {{TRUNK}}, then run:

   ```sh
   git-spice log long
   git-spice stack restack
   ```

   Run these commands inside each feature folder. Do not change the feature worktree to {{TRUNK}}. If an unexpected external dependency remains, reconcile it before restacking.

4. If `pending-features` exists, inspect it as part of the same pass. If a frozen gate remains open, preserve that snapshot and report the affected group as held. Do not blindly restack the pending chain onto {{TRUNK}}. For gates that have cleared, use the promotion workflow above. A scoped upstack restack is allowed only when it cannot cross a frozen descendant. Verify all remaining frozen commits afterward.
5. Resolve each interrupted restack before starting the next worktree. Inspect and stage the conflict resolutions, then use `git-spice rebase continue`. Use `git-spice rebase abort` if the operation must be rolled back. Check the final diffs and run the relevant tests and lint checks.
6. When publication is authorized, submit each affected stack from its own worktree with git-spice. For existing PRs, use `git-spice stack submit --update-only`. Verify GitHub heads and bases. Do not submit unrelated stacks or frozen branches as a side effect.
7. Remove a completed worktree only after its stack has no branches and no uncommitted work would be lost. Update TOC entries for changed stack membership, worktree paths, or statuses. A routine merge or restack does not require rewriting the whole TOC. Report which worktrees were restacked, which groups remain held, and any unresolved checks.

## Code and review conventions

Use [explain](skills/explain/SKILL.md) for clear user-facing prose.
Use [atomic-prs](skills/atomic-prs/SKILL.md) when planning or changing stacks,
[code-review](skills/code-review/SKILL.md) for requested reviews,
[write-readable-code](skills/write-readable-code/SKILL.md) and
[name-code](skills/name-code/SKILL.md) for code changes, and
[unit-testing](skills/unit-testing/SKILL.md) for tests.
Read each worktree's repository instructions and use its supported language versions and checks.
Inspect `git-spice log long` before stack changes. Check installed CLI help for syntax.
Use `git-spice` for branch navigation and stack operations. Do not install it without authorization.
If unavailable, report this and use ordinary Git. Do not publish without task authorization.
Agents may work on different feature worktrees at once. Shared Git and git-spice metadata
changes must run one at a time across the workspace. Coordinate ownership before changing it.
Do not start other agents unless the task or repository instructions authorize delegation.
