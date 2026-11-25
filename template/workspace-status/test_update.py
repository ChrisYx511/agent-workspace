"""Exercise the updater through its CLI using real temporary files and processes."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path


class DashboardUpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        status = self.root / "workspace-status"
        (status / "items").mkdir(parents=True)
        shutil.copyfile(Path(__file__).with_name("update.py"), status / "update.py")
        self.record = json.loads(Path(__file__).with_name("example.json").read_text())

    def update(self, task_id=None, record=None):
        command = [sys.executable, str(self.root / "workspace-status/update.py")]
        if task_id:
            command.append(task_id)
        return subprocess.run(
            command,
            check=False,
            input=json.dumps(record or self.record),
            capture_output=True,
            text=True,
        )

    def test_update_shows_order_remaining_work_and_deferred_scope(self):
        self.record["steps"] = [
            {"name": "Read", "status": "done"},
            {"name": "Edit", "status": "in_progress"},
            {"name": "Link results", "status": "deferred"},
        ]
        result = self.update("feature-agent")
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(
            (self.root / "workspace-status/items/feature-agent.json").read_text()
        )
        self.assertIn("updated_at", saved)
        dashboard = (self.root / "DASHBOARD.html").read_text()
        self.assertIn("1/2 done; 1 left; 1 deferred", dashboard)
        self.assertIn("Build / PR order", dashboard)
        self.assertIn("Link results", dashboard)
        self.assertTrue(dashboard.startswith("<!doctype html>"))
        self.assertIn('value="1" max="2"', dashboard)
        self.assertIn('for="progress-task-feature-agent"', dashboard)
        self.assertNotIn("<script", dashboard)
        parser = HTMLParser()
        parser.feed(dashboard)

    def test_concurrent_agents_keep_every_record_and_dashboard_entry(self):
        ids = [f"feature-agent-{i}" for i in range(8)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(self.update, ids))
        self.assertTrue(all(result.returncode == 0 for result in results))
        self.assertEqual(
            len(list((self.root / "workspace-status/items").glob("*.json"))), 8
        )
        dashboard = (self.root / "DASHBOARD.html").read_text()
        for item_id in ids:
            self.assertIn(f"items/{item_id}.json", dashboard)

    def test_another_owner_cannot_overwrite_a_record(self):
        self.assertEqual(self.update("owned-task").returncode, 0)
        before = (self.root / "DASHBOARD.html").read_bytes()
        self.record["agent"] = "another-agent"
        self.assertNotEqual(self.update("owned-task").returncode, 0)
        self.assertEqual((self.root / "DASHBOARD.html").read_bytes(), before)
        saved = json.loads(
            (self.root / "workspace-status/items/owned-task.json").read_text()
        )
        self.assertEqual(saved["agent"], "unique-agent-session")

    def test_invalid_completion_does_not_change_existing_files(self):
        self.assertEqual(self.update("existing-task").returncode, 0)
        before = (self.root / "DASHBOARD.html").read_bytes()
        self.record["status"] = "complete"
        self.assertNotEqual(self.update("bad-completion").returncode, 0)
        self.assertFalse(
            (self.root / "workspace-status/items/bad-completion.json").exists()
        )
        self.assertEqual((self.root / "DASHBOARD.html").read_bytes(), before)

    def test_regeneration_keeps_record_timestamp_and_escapes_markup(self):
        self.record["feature"] = "[remote image](https://example.invalid) <script> & |"
        self.assertEqual(self.update("safe-record").returncode, 0)
        path = self.root / "workspace-status/items/safe-record.json"
        before = path.read_bytes()
        self.assertEqual(self.update().returncode, 0)
        self.assertEqual(path.read_bytes(), before)
        dashboard = (self.root / "DASHBOARD.html").read_text()
        self.assertNotIn("<script>", dashboard)
        self.assertIn("[remote image]", dashboard)
        self.assertIn("&lt;script&gt; &amp; |", dashboard)

    def test_unassigned_seed_can_be_claimed_and_task_id_cannot_escape_items(self):
        self.record["agent"] = "unassigned"
        self.record["status"] = "needs_update"
        self.assertEqual(self.update("seed-task").returncode, 0)
        self.record["agent"] = "main-session"
        self.assertEqual(self.update("seed-task").returncode, 0)
        self.assertNotEqual(self.update("../outside").returncode, 0)
        self.assertFalse((self.root / "workspace-status/outside.json").exists())


if __name__ == "__main__":
    unittest.main()
