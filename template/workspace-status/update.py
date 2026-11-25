"""Update one agent's task and rebuild the workspace dashboard (Python 3.12+)."""

import argparse
import fcntl
import html
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG_PATH = Path(__file__).resolve().parent.parent / "workspace.json"
CONFIG = (
    json.loads(CONFIG_PATH.read_text())
    if CONFIG_PATH.exists()
    else {"project": "Workspace Template", "timezone": "UTC"}
)

STATES = ("in_progress", "blocked", "needs_update", "backlog", "complete")
STEP_STATES = ("pending", "in_progress", "done", "deferred")
FIELDS = (
    "feature",
    "task",
    "agent",
    "work_order",
    "worktree",
    "status",
    "current_step",
    "next_action",
)


def validate(record):
    """Reject incomplete updates before changing any saved status."""
    for field in FIELDS:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"{field} must be a nonempty string")
    if record["status"] not in STATES:
        raise ValueError(f"status must be one of {STATES}")
    for field in ("order", "blockers", "checks"):
        if not isinstance(record.get(field), list) or not all(
            isinstance(item, str) and item.strip() for item in record[field]
        ):
            raise ValueError(f"{field} must be a list of nonempty strings")
    if not isinstance(record.get("steps"), list) or not record["steps"]:
        raise ValueError("steps must be a nonempty list")
    for step in record["steps"]:
        if (
            not isinstance(step, dict)
            or not isinstance(step.get("name"), str)
            or not step["name"].strip()
        ):
            raise ValueError("each step needs a nonempty name")
        if step.get("status") not in STEP_STATES:
            raise ValueError(f"step status must be one of {STEP_STATES}")
    if record["status"] == "complete" and any(
        step["status"] in ("pending", "in_progress") for step in record["steps"]
    ):
        raise ValueError("complete tasks cannot have pending or in-progress steps")
    stamp = datetime.fromisoformat(record["updated_at"])
    if stamp.utcoffset() is None:
        raise ValueError("updated_at must include a timezone")


def text(value):
    """Escape record text before placing it in HTML."""
    return html.escape(value).replace("\n", "<br>")


def render(records, now):
    """Show completed steps and remaining scope without estimating effort."""
    css = """
    :root{
    color-scheme:light;
    font:16px/1.55 system-ui,sans-serif;
    color:#172b3b;
    background:#f3f6f8}
    *{
    box-sizing:border-box}
    body{
    margin:0}
    main{
    max-width:1280px;
    margin:auto;
    padding:40px 24px}
    h1{
    font-size:clamp(28px,4vw,44px);
    line-height:1.15;
    margin:8px 0 16px}
    h2{
    font-size:22px;
    margin:0}
    h3{
    font-size:16px;
    margin:24px 0 8px}
    p{
    margin:8px 0 16px}
    a{
    color:#075d8b;
    text-underline-offset:3px}
    .eyebrow,.muted,dt{
    color:#536677;
    font-size:14px}
    .lead{
    font-size:18px;
    max-width:930px}
    nav{
    display:flex;
    flex-wrap:wrap;
    gap:18px;
    margin:20px 0}
    .metrics{
    display:flex;
    gap:12px;
    flex-wrap:wrap;
    margin:24px 0}
    .metric{
    flex:1;
    min-width:140px;
    background:white;
    padding:16px 20px;
    border:1px solid #d4dfe7;
    border-radius:10px}
    .metric strong{
    display:block;
    font-size:28px}
    .scroll{
    overflow-x:auto}
    table{
    border-collapse:collapse;
    width:100%;
    background:white}
    th,td{
    text-align:left;
    vertical-align:top;
    border-bottom:1px solid #d4dfe7;
    padding:12px;
    font-size:14px}
    th{
    background:#e8eef3}
    td:first-child{
    min-width:190px}
    td a{
    font-weight:650}
    .tasks{
    display:grid;
    gap:20px;
    margin-top:30px}
    article{
    background:white;
    border:1px solid #d4dfe7;
    border-radius:12px;
    padding:24px;
    scroll-margin-top:20px}
    .task-head{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:20px}
    .subtitle{
    margin-top:5px;
    color:#536677}
    .badge{
    display:inline-block;
    padding:4px 9px;
    border-radius:6px;
    font-size:13px;
    white-space:nowrap;
    background:#e8eef3}
    .in_progress{
    background:#def1f0;
    color:#145b58}
    .blocked,.needs_update{
    background:#fff0c8;
    color:#704700}
    .complete{
    background:#e3efdf;
    color:#305126}
    .backlog,.deferred{
    background:#eceaf6;
    color:#51466c}
    dl{
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:16px;
    margin:20px 0}
    dd{
    margin:3px 0 0;
    overflow-wrap:anywhere}
    .now{
    border-left:3px solid #13877f;
    padding:10px 16px;
    background:#f0f8f7;
    margin:16px 0}
    .now p:last-child{
    margin-bottom:0}
    .order{
    padding-left:24px}
    .order li{
    margin:5px 0}
    .progress{
    margin:20px 0}
    progress{
    width:100%;
    height:10px;
    accent-color:#13877f}
    .steps{
    list-style:none;
    padding:0}
    .steps li{
    display:flex;
    justify-content:space-between;
    gap:16px;
    padding:9px 0;
    border-bottom:1px solid #e6edf2}
    .evidence{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:24px}
    .evidence ul{
    padding-left:20px;
    margin-top:6px}
    .evidence li{
    margin:7px 0;
    overflow-wrap:anywhere}
    footer{
    margin-top:30px;
    color:#536677;
    font-size:14px}
    @media(max-width:700px){
    main{
    padding:24px 14px}
    article{
    padding:18px}
    .task-head{
    display:block}
    .task-head .badge{
    margin-bottom:10px}
    dl{
    grid-template-columns:1fr 1fr}
    .evidence{
    grid-template-columns:1fr;
    gap:0}
    .steps li{
    align-items:flex-start}
    }
    @media print{
    body{
    background:white}
    main{
    padding:0;
    max-width:none}
    nav{
    display:none}
    .scroll{
    overflow:visible}
    article{
    break-inside:avoid;
    padding:16px}
    th,td{
    font-size:11px;
    padding:8px}
    a{
    color:inherit}
    .metrics{
    gap:8px}
    .metric{
    padding:8px}
    h1{
    font-size:28px}
    }
    """
    lines = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        (
            '<meta name="description" content="Agent-reported workspace tasks, '
            'build order, progress and remaining work">'
        ),
        f"<title>{text(CONFIG['project'])} — Workspace dashboard</title><style>{css}</style></head><body><main>",
        f'<header><div class="eyebrow">{text(CONFIG["project"])} · WORKSPACE</div>',
        "<h1>What is being worked on</h1>",
        (
            '<p class="lead">Features, work orders, current steps and remaining work, '
            "reported by each owning agent.</p>"
        ),
        f'<p class="muted">Generated {now:%Y-%m-%d %H:%M:%S %Z} · {text(CONFIG["timezone"])}</p>',
        '<nav aria-label="Workspace references"><a href="TOC.md">Stack inventory</a>',
        '<a href="workspace-status/README.md">Update instructions</a></nav>',
        (
            '<p class="muted">Updates happen during work; no background monitor is running. '
            "Check each record’s timestamp. A missing or old update does not mean work has finished. "
            "Only reported tasks appear here.</p></header>"
        ),
        '<div class="metrics" aria-label="Reported task counts">',
    ]
    for status, label in (
        ("in_progress", "Working"),
        ("blocked", "Blocked"),
        ("needs_update", "Needs confirmation"),
        ("backlog", "Backlog"),
        ("complete", "Complete"),
    ):
        count = sum(record["status"] == status for _, record in records)
        lines.append(f'<div class="metric"><strong>{count}</strong>{label}</div>')
    lines.extend(
        [
            (
                '</div><p class="muted">Progress counts completed steps, not time or effort. '
                "Deferred work is separate. An Active stack in TOC.md does not imply "
                "an agent is working on it.</p>"
            ),
            '<div class="scroll"><table><caption class="muted">Reported tasks</caption>',
            '<thead><tr><th scope="col">Feature / task</th><th scope="col">Agent</th>',
            '<th scope="col">Status</th><th scope="col">Progress</th>',
            '<th scope="col">Current step</th><th scope="col">Updated</th></tr></thead><tbody>',
        ]
    )
    details = []
    for item_id, record in records:
        done = sum(step["status"] == "done" for step in record["steps"])
        deferred = sum(step["status"] == "deferred" for step in record["steps"])
        total = len(record["steps"]) - deferred
        remaining = total - done
        progress = f"{done}/{total} done; {remaining} left; {deferred} deferred"
        stamp = datetime.fromisoformat(record["updated_at"]).astimezone(now.tzinfo)
        stale = record["status"] in ("in_progress", "needs_update") and (
            record["status"] == "needs_update" or (now - stamp).total_seconds() > 3600
        )
        state = text(record["status"].replace("_", " ")) + (
            " — confirm status" if stale else ""
        )
        badge = f'<span class="badge {record["status"]}">{state}</span>'
        anchor = text(f"task-{item_id}")
        source = f"workspace-status/items/{text(item_id)}.json"
        lines.append(
            f'<tr><td><a href="#{anchor}">{text(record["feature"])}</a><br>'
            f"{text(record['task'])}</td>"
            f"<td>{text(record['agent'])}</td><td>{badge}</td><td>{progress}</td>"
            f"<td>{text(record['current_step'])}</td><td>{stamp:%Y-%m-%d %H:%M %Z}</td></tr>"
        )
        details.extend(
            [
                (
                    f'<article id="{anchor}"><div class="task-head"><div>'
                    f"<h2>{text(record['feature'])}</h2>"
                ),
                f'<p class="subtitle">{text(record["task"])}</p></div>{badge}</div><dl>',
            ]
        )
        for label, value in (
            ("Owner", record["agent"]),
            ("Work order", record["work_order"]),
            ("Worktree", record["worktree"]),
            ("Last update", f"{stamp:%Y-%m-%d %H:%M %Z}"),
        ):
            details.append(f"<div><dt>{label}</dt><dd>{text(value)}</dd></div>")
        details.extend(
            [
                '</dl><div class="now">',
                f"<p><strong>Now:</strong> {text(record['current_step'])}</p>",
                f"<p><strong>Next action:</strong> {text(record['next_action'])}</p></div>",
                '<h3>Build / PR order</h3><ol class="order">',
            ]
        )
        details.extend(f"<li>{text(item)}</li>" for item in record["order"])
        if not record["order"]:
            details.append("<li>Not assigned.</li>")
        details.extend(
            [
                '</ol><div class="progress">',
                f'<label for="progress-{anchor}">{progress}</label>',
                (
                    f'<progress id="progress-{anchor}" value="{done}" max="{max(total, 1)}">'
                    f'{done} of {total} active steps complete</progress></div><ul class="steps">'
                ),
            ]
        )
        details.extend(
            f'<li><span>{text(step["name"])}</span><span class="badge {step["status"]}">'
            f"{text(step['status'].replace('_', ' '))}</span></li>"
            for step in record["steps"]
        )
        details.append('</ul><div class="evidence">')
        for label, field in (
            ("Blockers / decisions", "blockers"),
            ("Checks / evidence", "checks"),
        ):
            details.append(f"<section><h3>{label}</h3><ul>")
            details.extend(f"<li>{text(item)}</li>" for item in record[field])
            if not record[field]:
                details.append("<li>None reported.</li>")
            details.append("</ul></section>")
        details.append(
            f'</div><p class="muted"><a href="{source}">Source record</a></p></article>'
        )
    lines.append("</tbody></table></div>")
    if not records:
        lines.append("<p>No task records yet.</p>")
    lines.extend(
        [
            '<div class="tasks">',
            *details,
            "</div>",
            (
                "<footer>Generated from independent agent-owned records. "
                "Refresh this file after agents update their progress.</footer>"
            ),
            "</main></body></html>",
        ]
    )
    return "\n".join(lines) + "\n"


def atomic_write(path, content):
    """Readers see either the old complete file or the new complete file."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as file:
        pending = Path(file.name)
        try:
            file.write(content)
            file.close()
            os.replace(pending, path)
        finally:
            pending.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task_id",
        nargs="?",
        help="unique task/agent slug; read its full JSON update from stdin",
    )
    args = parser.parse_args()
    if args.task_id and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.task_id):
        parser.error("task_id must be a lowercase hyphenated slug")
    root = Path(__file__).resolve().parent.parent
    status = root / "workspace-status"
    items = status / "items"
    now = datetime.now(ZoneInfo(CONFIG["timezone"]))
    incoming = json.load(sys.stdin) if args.task_id else None
    if args.task_id:
        if not isinstance(incoming, dict):
            parser.error("the update must be a JSON object")
        incoming["updated_at"] = now.isoformat(timespec="seconds")
        validate(incoming)
    with (status / ".update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in items.glob("*.json")
        }
        if args.task_id:
            existing = records.get(args.task_id)
            if existing and existing["agent"] not in (incoming["agent"], "unassigned"):
                raise ValueError(
                    "this record belongs to another agent; use your own task ID"
                )
            records[args.task_id] = incoming
        for record in records.values():
            validate(record)
        ordered = sorted(
            records.items(),
            key=lambda item: (
                STATES.index(item[1]["status"]),
                item[1]["feature"],
                item[0],
            ),
        )
        dashboard = render(ordered, now)
        if args.task_id:
            atomic_write(
                items / f"{args.task_id}.json",
                json.dumps(incoming, indent=2, ensure_ascii=False) + "\n",
            )
        atomic_write(root / "DASHBOARD.html", dashboard)
    print(root / "DASHBOARD.html")


if __name__ == "__main__":
    main()
