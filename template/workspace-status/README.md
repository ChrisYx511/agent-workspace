# Workspace progress records

[Open the dashboard](../DASHBOARD.html). This is a live work log, separate from the stack inventory in `TOC.md`.

Each independently owned task has one JSON file in `items/`. Agents update only their own records. Parallel subtasks use different task IDs, even if they share a feature or work order. The dashboard combines all records. It does not imply that every stack has an agent working on it.

## Update a task

1. Copy `example.json` to a temporary file **outside `items/`** and fill in the whole record. Use a stable owner name for this agent/session. Use actual work orders and PR numbers; mark planned increments as planned.
2. Submit the update from the workspace root:

   ```sh
   python3 workspace-status/update.py condition-rows-main < /tmp/condition-rows-status.json
   ```

   From a feature worktree, use `python3 ../workspace-status/update.py TASK_ID < /tmp/status.json`.

3. Verify the resulting `DASHBOARD.html`. The script stamps the record with the configured workspace time. Do not edit generated HTML or saved JSON files directly.

Python 3.12+ on macOS/Linux is sufficient. No dependencies or server are needed. Running the script without a task ID regenerates the dashboard without changing records or making their timestamps look fresh:

```sh
python3 workspace-status/update.py
```

Updates use a file lock and atomic replacement. Updates to different records do not overwrite one another. An existing record cannot change to another named owner. To take over work, create your own record and name the previous task in `checks`; the previous owner should mark their task complete with a handoff note. An `unassigned` seed can be claimed by its actual owner.

## What to record

- `feature`: user-facing feature name. Related agents use the same feature name.
- `task`: the outcome this agent owns, not the whole feature unless it owns all of it.
- `agent`: a stable, distinct agent/session label. `unassigned` is reserved for seed records needing confirmation.
- `work_order`: the actual work order, or `Unassigned` if none exists.
- `worktree`: workspace-relative directory, or `workspace root`.
- `status`: `in_progress`, `blocked`, `needs_update`, `backlog`, or `complete`.
- `current_step`: what is happening now. Say when a check is running or when status is not confirmed.
- `order`: prerequisites and build/PR order. Distinguish current branches from planned PRs.
- `steps`: meaningful outcomes, each `pending`, `in_progress`, `done`, or `deferred`.
- `next_action`: the next concrete action or the condition needed to resume.
- `blockers`: actual blockers and unresolved decisions. An empty list means none reported.
- `checks`: concise evidence with revision, result, and limits where known. Separate old test results from checks on the current split.

The dashboard calculates completed and remaining steps. This is scope progress, not a time estimate. A deferred step does not count as completed or remaining active work. Do not split steps or mark them done just to improve the number.

## Freshness and lifecycle

Update at task start, when scope changes, at meaningful milestones, when a blocker appears or clears, and before handoff or the final answer. During sustained work, refresh at least every ten minutes when control returns between operations. Do not stop a test or edit shared history merely to update status.

Before starting, inspect existing records and avoid duplicating an owned task. A record older than one hour is a prompt to confirm status, not permission to take over. At generation time, stale running records and `needs_update` seeds are marked for confirmation. Timestamps remain visible after generation; this dashboard has no background monitor or automatic clock refresh.

Keep completed records as history. A paused or interrupted task must not be marked complete. Use `needs_update` when the agent is no longer actively working and the actual resume state is uncertain. `TOC.md` remains the stack membership/base/status inventory; update it separately when the workspace rules require it.

Check the updater with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s workspace-status -p 'test_*.py'
```
