# Pending work and frozen boundaries

No frozen branches or pending groups exist at setup. Do not create them by default.
Use independent feature stacks rooted at `{{TRUNK}}` whenever possible.

When an existing repository requires migration, record every pending group, exact frozen
commit, required replacement feature, and release condition here and in [TOC.md](TOC.md).
Frozen branches preserve prerequisite history. Do not advance, restack across, submit PRs
for, or merge these snapshots. Do not merge pending work into them.

Before extraction, inspect the live graph, record heads and bases for recovery, preserve
uncommitted work, and verify the required behavior on the synced trunk. Plan how every
remaining descendant keeps its prerequisites. Move only the verified feature subset.
Preserve PR identities and check each affected immediate-parent diff. Retire a frozen
boundary only when no remaining descendant needs it. Keep unreleased groups blocked.

If a `pending-features` worktree is needed, set its worktree-local
`spice.submit.updateOnly=true` guard and use explicit `--update-only` submissions.
See [NAVIGATE.md](NAVIGATE.md) for the promotion and synchronization workflow.
