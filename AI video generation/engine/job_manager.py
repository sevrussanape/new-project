"""Persistent single-worker job queue for local video rendering.

Job metadata survives restarts in SQLite. Active inference is intentionally not
resumed after a crash: interrupted jobs are marked failed with a clear reason.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .video_engine import generate_video
from .production_pipeline import produce_video


class JobManager:
    def __init__(self, output_dir: Path, *, database: Path | None = None, max_pending: int = 3):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.database = Path(database) if database else self.output_dir.parent / "studio_jobs.sqlite3"
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.max_pending = max(1, int(max_pending))
        self._jobs: dict[str, dict[str, Any]] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._tasks: dict[str, dict[str, Any]] = {}
        self._queue: list[str] = []
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._initialize_database()
        self._restore_history()
        threading.Thread(target=self._worker, daemon=True, name="offline-studio-jobs").start()

    @contextmanager
    def _database(self):
        conn = sqlite3.connect(self.database, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self) -> None:
        with self._database() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, progress REAL NOT NULL,
                message TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
                prompt TEXT NOT NULL, mode TEXT NOT NULL, output TEXT, error TEXT,
                engine TEXT, is_generative_ai INTEGER, description TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")

    def _restore_history(self) -> None:
        with self._database() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 200").fetchall()
        for row in rows:
            item = dict(row)
            if item["status"] in {"queued", "running"}:
                item.update(status="failed", progress=0.0,
                            message="Interrupted because the studio restarted",
                            error="This job was interrupted by an application restart. Start it again.",
                            updated_at=time.time())
                self._save(item)
            if item.get("is_generative_ai") is not None:
                item["is_generative_ai"] = bool(item["is_generative_ai"])
            self._jobs[item["id"]] = item

    def _save(self, item: dict[str, Any]) -> None:
        fields = ("id", "status", "progress", "message", "created_at", "updated_at",
                  "prompt", "mode", "output", "error", "engine", "is_generative_ai", "description")
        values = [item.get(k) for k in fields]
        with self._database() as db:
            db.execute(f"INSERT OR REPLACE INTO jobs ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", values)

    def submit(self, task: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if len(self._queue) >= self.max_pending:
                raise RuntimeError(f"The local queue is full ({self.max_pending} waiting jobs). Wait for a job to finish.")
            job_id = uuid.uuid4().hex[:12]
            now = time.time()
            item = {"id": job_id, "status": "queued", "progress": 0.0,
                    "message": "Waiting for the local render engine", "created_at": now,
                    "updated_at": now, "prompt": task.get("prompt", ""),
                    "mode": task.get("mode", "text"), "output": None, "error": None,
                    "engine": None, "is_generative_ai": None, "description": None}
            self._jobs[job_id] = item
            self._cancel[job_id] = threading.Event()
            self._tasks[job_id] = task
            self._queue.append(job_id)
            self._save(item)
            self._wake.set()
            return dict(item)

    def _update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            item = self._jobs.get(job_id)
            if item:
                item.update(fields, updated_at=time.time())
                self._save(item)

    def _worker(self) -> None:
        while True:
            self._wake.wait()
            while True:
                with self._lock:
                    if not self._queue:
                        self._wake.clear()
                        break
                    job_id = self._queue.pop(0)
                    job = self._jobs.get(job_id)
                    cancel = self._cancel.get(job_id)
                    task = self._tasks.get(job_id)
                if not job or not cancel:
                    continue
                if cancel.is_set():
                    self._update(job_id, status="cancelled", message="Cancelled before start")
                    self._cleanup(job_id)
                    continue
                self._update(job_id, status="running", progress=0.01, message="Starting local engine")
                output = self.output_dir / f"{job_id}.mp4"
                try:
                    runner = produce_video if (task or {}).get('mode') == 'production' else generate_video
                    result = runner(task or {}, output, cancel_event=cancel,
                        progress=lambda p, m: self._update(job_id, progress=max(0.0, min(1.0, float(p))), message=str(m)[:300]))
                    self._update(job_id, status="completed", progress=1.0, message="Video ready",
                                 output=f"/outputs/{output.name}", engine=result.get("engine"),
                                 is_generative_ai=result.get("is_generative_ai"), description=result.get("description"))
                except Exception as exc:
                    status = "cancelled" if cancel.is_set() else "failed"
                    output.unlink(missing_ok=True)
                    self._update(job_id, status=status, message="Generation did not complete", error=str(exc)[:1500])
                finally:
                    self._cleanup(job_id)

    def _cleanup(self, job_id: str) -> None:
        with self._lock:
            task = self._tasks.pop(job_id, None)
            self._cancel.pop(job_id, None)
        image_path = (task or {}).get("image_path") if isinstance(task, dict) else None
        if image_path:
            try:
                Path(image_path).unlink(missing_ok=True)
            except OSError:
                pass

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._jobs.get(job_id)
            return dict(item) if item else None

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = sorted(self._jobs.values(), key=lambda x: x["created_at"], reverse=True)[:max(1, min(200, limit))]
            return [dict(x) for x in items]

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancel.get(job_id)
            if not event:
                return False
            event.set()
            if self._jobs.get(job_id, {}).get("status") == "queued":
                self._update(job_id, status="cancelled", message="Cancelled by user")
            return True