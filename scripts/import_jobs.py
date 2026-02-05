from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class ImportJobError(RuntimeError):
    pass


def validate_virtual_root(root_path: str) -> None:
    if root_path is None:
        return
    lowered = root_path.lower()
    first_segment = root_path.split("/")[0]
    if ":" in first_segment or lowered.startswith("c:/") or lowered.startswith("d:/"):
        raise ValueError(
            f"--root-path looks like a local path ('{root_path}'). "
            "Use a virtual path such as '' or '/2024/Trip'."
        )


def build_job_payload(
    input_dir: str,
    root_path: str,
    dry_run: bool,
    requested_by: Optional[str] = None,
    worker_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not input_dir or not input_dir.strip():
        raise ValueError("input_dir is required")
    validate_virtual_root(root_path or "")

    payload: Dict[str, Any] = {
        "inputDir": input_dir,
        "rootPath": root_path or "",
        "dryRun": bool(dry_run),
    }
    if requested_by:
        payload["requestedBy"] = requested_by
    if worker_id:
        payload["workerId"] = worker_id
    return payload


def enqueue_job(
    endpoint: str,
    payload: Dict[str, Any],
    timeout_sec: int = 10,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if not endpoint or not endpoint.strip():
        raise ValueError("endpoint is required")

    body = json.dumps(payload).encode("utf-8")
    merged_headers = {"content-type": "application/json"}
    if headers:
        merged_headers.update(headers)
    req = urllib.request.Request(endpoint, data=body, headers=merged_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            if resp.status < 200 or resp.status >= 300:
                raise ImportJobError(f"enqueue failed with status {resp.status}")
    except urllib.error.HTTPError as exc:
        raise ImportJobError(f"enqueue failed with status {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ImportJobError(f"enqueue failed: {exc.reason}") from exc

    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ImportJobError("invalid JSON response from endpoint") from exc
    else:
        data = {}

    job_id = data.get("jobId") or data.get("job_id")
    if not job_id:
        raise ImportJobError("enqueue response did not include jobId")

    return {"job_id": job_id, "response": data}
