import tempfile
import time
import unittest
from pathlib import Path

from engine.job_manager import JobManager


class JobManagerPersistenceTests(unittest.TestCase):
    def test_interrupted_jobs_are_restored_as_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = JobManager(root / "outputs", database=root / "jobs.sqlite3")
            now = time.time()
            record = {
                "id": "interrupted01", "status": "running", "progress": 0.42,
                "message": "Rendering", "created_at": now, "updated_at": now,
                "prompt": "test prompt", "mode": "image-motion", "output": None,
                "error": None, "engine": None, "is_generative_ai": None, "description": None,
            }
            manager._save(record)
            restored = JobManager(root / "outputs", database=root / "jobs.sqlite3")
            job = restored.get("interrupted01")
            self.assertEqual(job["status"], "failed")
            self.assertIn("restarted", job["message"])
            self.assertIn("interrupted", job["error"])

    def test_job_history_is_saved_to_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = JobManager(root / "outputs", database=root / "jobs.sqlite3")
            job = manager.submit({"mode": "image-motion", "prompt": "persistent test"})
            deadline = time.time() + 3
            while time.time() < deadline and manager.get(job["id"])["status"] == "queued":
                time.sleep(0.02)
            with manager._database() as db:
                row = db.execute("SELECT id, prompt FROM jobs WHERE id=?", (job["id"],)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["prompt"], "persistent test")
            manager.cancel(job["id"])


if __name__ == "__main__":
    unittest.main()
