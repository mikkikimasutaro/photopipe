#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from warnings_config import configure_warning_filters

configure_warning_filters()

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import pubsub_v1

SCRIPT_PATH = Path(__file__).with_name("import_photos.py")
DEFAULT_SERVICE_ACCOUNT_PATH = Path(__file__).resolve().parents[1] / "mikkikicom-firebase-adminsdk-fbsvc-06bdbf6b0d.json"

IMPORT_JOBS_COLLECTION = os.getenv("IMPORT_JOBS_COLLECTION", "importJobs").strip()
IMPORT_JOBS_SUBSCRIPTION = os.getenv("IMPORT_JOBS_SUBSCRIPTION", "").strip()
SUBPROCESS_TIMEOUT_SEC = int(os.getenv("IMPORT_JOB_TIMEOUT_SEC", "21600"))
LOG_TAIL = 2000
RET_TAIL = 20000


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str) -> None:
    level = os.getenv("IMPORT_WORKER_LOG_LEVEL", "info").strip().lower()
    if level in {"quiet", "silent", "none"}:
        return
    sys.stderr.write(f"[import_worker] {_ts()} {msg}\n")
    sys.stderr.flush()


def _tail(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    return s[-n:]


def _init_firestore() -> firestore.Client:
    if firebase_admin._apps:
        return firestore.client()

    path_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or os.getenv("firebase_service_account_path")
    if not path_env:
        path_env = str(DEFAULT_SERVICE_ACCOUNT_PATH)
    if not Path(path_env).exists():
        raise SystemExit(f"Service account JSON not found: {path_env}")
    cred = credentials.Certificate(path_env)
    firebase_admin.initialize_app(cred)
    return firestore.client()


def _update_job(db: firestore.Client, job_id: str, data: Dict[str, Any]) -> None:
    doc = db.collection(IMPORT_JOBS_COLLECTION).document(job_id)
    doc.set(data, merge=True)


def _run_import_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    input_dir = payload.get("inputDir")
    root_path = payload.get("rootPath", "")
    dry_run = bool(payload.get("dryRun", False))

    if not input_dir:
        return {"ok": False, "error": "inputDir is required"}
    if not SCRIPT_PATH.exists():
        return {"ok": False, "error": f"import_photos.py not found at {SCRIPT_PATH}"}

    cmd = [sys.executable, str(SCRIPT_PATH), "--input-dir", input_dir]
    if root_path:
        cmd += ["--root-path", root_path]
    if dry_run:
        cmd += ["--dry-run"]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    t0 = time.time()
    try:
        cp = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=SUBPROCESS_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as exc:
        dt = time.time() - t0
        return {
            "ok": False,
            "error": f"subprocess timeout (> {SUBPROCESS_TIMEOUT_SEC}s)",
            "elapsedSec": round(dt, 3),
            "stdoutTail": _tail(getattr(exc, "stdout", None), RET_TAIL),
            "stderrTail": _tail(getattr(exc, "stderr", None), RET_TAIL),
        }

    dt = time.time() - t0
    return {
        "ok": cp.returncode == 0,
        "exitCode": cp.returncode,
        "elapsedSec": round(dt, 3),
        "stdoutTail": _tail(cp.stdout, RET_TAIL),
        "stderrTail": _tail(cp.stderr, RET_TAIL),
    }


def _handle_message(db: firestore.Client, message: pubsub_v1.subscriber.message.Message) -> None:
    payload = json.loads(message.data.decode("utf-8"))
    job_id = payload.get("jobId")
    if not job_id:
        _log("message missing jobId, acking")
        message.ack()
        return

    _log(f"job {job_id} start")
    _update_job(db, job_id, {"status": "running", "startedAt": firestore.SERVER_TIMESTAMP})

    result = _run_import_job(payload)
    if result.get("ok"):
        _update_job(
            db,
            job_id,
            {"status": "done", "finishedAt": firestore.SERVER_TIMESTAMP, **result},
        )
        _log(f"job {job_id} done")
        message.ack()
        return

    _update_job(
        db,
        job_id,
        {"status": "error", "finishedAt": firestore.SERVER_TIMESTAMP, **result},
    )
    _log(f"job {job_id} failed")
    message.nack()


def main() -> None:
    if not IMPORT_JOBS_SUBSCRIPTION:
        raise SystemExit("IMPORT_JOBS_SUBSCRIPTION is required")

    db = _init_firestore()
    subscriber = pubsub_v1.SubscriberClient()
    future = subscriber.subscribe(IMPORT_JOBS_SUBSCRIPTION, callback=lambda msg: _handle_message(db, msg))
    _log(f"listening on {IMPORT_JOBS_SUBSCRIPTION}")

    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()


if __name__ == "__main__":
    main()
