#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from warnings_config import configure_warning_filters

configure_warning_filters()

import anyio
import firebase_admin
from firebase_admin import credentials, db
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SERVICE_ACCOUNT = BASE_DIR / "mikkikicom-firebase-adminsdk-fbsvc-06bdbf6b0d.json"


def log(message: str) -> None:
    sys.stderr.write(f"[relay] {message}\n")
    sys.stderr.flush()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _load_service_account() -> Dict[str, Any] | None:
    json_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or os.getenv(
        "firebase_service_account_json"
    )
    if json_env:
        return json.loads(json_env)

    path_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or os.getenv(
        "firebase_service_account_path"
    )
    if path_env and Path(path_env).exists():
        return json.loads(Path(path_env).read_text(encoding="utf-8"))

    if DEFAULT_SERVICE_ACCOUNT.exists():
        return json.loads(DEFAULT_SERVICE_ACCOUNT.read_text(encoding="utf-8"))

    client_email = os.getenv("FIREBASE_CLIENT_EMAIL") or os.getenv(
        "firebase_client_email"
    )
    private_key = os.getenv("FIREBASE_PRIVATE_KEY") or os.getenv(
        "firebase_private_key"
    )
    project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv(
        "firebase_project_id"
    )
    if client_email and private_key:
        return {
            "type": "service_account",
            "client_email": client_email,
            "private_key": private_key.replace("\\n", "\n"),
            "project_id": project_id,
        }

    return None


def init_firebase() -> None:
    database_url = os.getenv("FIREBASE_DATABASE_URL") or os.getenv(
        "firebase_database_url"
    )
    if not database_url:
        raise SystemExit("Missing FIREBASE_DATABASE_URL")

    if firebase_admin._apps:
        return

    service_account = _load_service_account()
    if service_account:
        cred = credentials.Certificate(service_account)
    else:
        cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(cred, {"databaseURL": database_url})


def claim_invite(invite_id: str) -> str:
    invite_ref = db.reference(f"device_invites/{invite_id}")
    invite = invite_ref.get()
    if not invite:
        raise SystemExit("Invite not found")
    if invite.get("status") != "pending":
        raise SystemExit(f"Invite not pending (status={invite.get('status')})")
    expires_at = invite.get("expiresAt")
    if expires_at and expires_at < _now_ms():
        raise SystemExit("Invite expired")

    device_id = str(uuid.uuid4())
    now = _now_ms()
    name = os.getenv("DEVICE_NAME") or invite.get("displayName") or "Local MCP"
    owner_id = invite.get("ownerId")
    if not owner_id:
        raise SystemExit("Invite is missing ownerId")

    updates = {
        f"device_invites/{invite_id}/status": "used",
        f"device_invites/{invite_id}/usedAt": now,
        f"device_invites/{invite_id}/deviceId": device_id,
        f"devices/{device_id}/meta": {
            "ownerId": owner_id,
            "displayName": name,
            "createdAt": now,
        },
        f"users/{owner_id}/devices/{device_id}": {
            "name": name,
            "createdAt": now,
            "status": "active",
        },
    }
    db.reference("/").update(updates)
    return device_id


async def _heartbeat(presence_ref: db.Reference) -> None:
    while True:
        presence_ref.update({"lastSeen": _now_ms()})
        await anyio.sleep(30)


async def _process_requests(session: ClientSession, device_id: str) -> None:
    requests_ref = db.reference(f"devices/{device_id}/requests")
    responses_ref = db.reference(f"devices/{device_id}/responses")

    while True:
        items = requests_ref.get() or {}
        if isinstance(items, dict):
            for request_id, req in items.items():
                if not isinstance(req, dict):
                    continue
                if req.get("status") != "pending":
                    continue

                expires_at = req.get("expiresAt")
                if expires_at and expires_at < _now_ms():
                    responses_ref.child(request_id).set(
                        {
                            "status": "error",
                            "error": {"message": "request expired"},
                            "completedAt": _now_ms(),
                        }
                    )
                    requests_ref.child(request_id).update(
                        {"status": "error", "completedAt": _now_ms()}
                    )
                    continue

                status_ref = requests_ref.child(f"{request_id}/status")

                def _claim(current):
                    return "processing" if current == "pending" else current

                try:
                    new_status = status_ref.transaction(_claim)
                except Exception:
                    continue
                if new_status != "processing":
                    continue

                name = req.get("name")
                if not name:
                    responses_ref.child(request_id).set(
                        {
                            "status": "error",
                            "error": {"message": "missing tool name"},
                            "completedAt": _now_ms(),
                        }
                    )
                    requests_ref.child(request_id).update(
                        {"status": "error", "completedAt": _now_ms()}
                    )
                    continue

                try:
                    log(f"tool call {name} ({request_id})")
                    result = await session.call_tool(name, req.get("arguments") or {})
                    responses_ref.child(request_id).set(
                        {
                            "status": "done",
                            "result": _serialize(result),
                            "completedAt": _now_ms(),
                        }
                    )
                    requests_ref.child(request_id).update(
                        {"status": "done", "completedAt": _now_ms()}
                    )
                except Exception as exc:
                    responses_ref.child(request_id).set(
                        {
                            "status": "error",
                            "error": {"message": str(exc)},
                            "completedAt": _now_ms(),
                        }
                    )
                    requests_ref.child(request_id).update(
                        {"status": "error", "completedAt": _now_ms()}
                    )
        await anyio.sleep(1)


async def run() -> None:
    init_firebase()

    device_id = os.getenv("MCP_DEVICE_ID") or os.getenv("mcp_device_id")
    if not device_id:
        invite_id = os.getenv("PAIRING_INVITE_ID") or os.getenv("pairing_invite_id")
        if not invite_id:
            raise SystemExit("Set MCP_DEVICE_ID or PAIRING_INVITE_ID")
        device_id = claim_invite(invite_id)
        log(f"paired deviceId={device_id}")

    mcp_url = os.getenv("MCP_SERVER_URL") or os.getenv("mcp_server_url") or "http://127.0.0.1:8000/sse"

    async with sse_client(mcp_url) as streams:
        async with ClientSession(
            *streams,
            client_info=types.Implementation(name="mcp-rtdb-relay", version="0.1.0"),
        ) as session:
            await session.initialize()
            log(f"connected to MCP server {mcp_url}")

            tools = await session.list_tools()
            db.reference(f"devices/{device_id}/tools").set(
                {"tools": _serialize(tools.tools), "updatedAt": _now_ms()}
            )

            presence_ref = db.reference(f"devices/{device_id}/presence")
            presence_ref.set(
                {"online": True, "lastSeen": _now_ms(), "pid": os.getpid()}
            )

            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(_heartbeat, presence_ref)
                    await _process_requests(session, device_id)
            finally:
                presence_ref.update({"online": False, "lastSeen": _now_ms()})


def main() -> None:
    anyio.run(run, backend="asyncio")


if __name__ == "__main__":
    main()
