from __future__ import annotations

import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

HOST = os.getenv("MCP_HOST", "127.0.0.1").strip()
PORT = int(os.getenv("MCP_PORT", "8000"))
MOUNT_PATH = os.getenv("MCP_MOUNT_PATH", "/").strip()

mcp = FastMCP(
    "Photo Import (Firestore/Storage)",
    json_response=True,
    host=HOST,
    port=PORT,
    mount_path=MOUNT_PATH,
)

SCRIPT_PATH = Path(__file__).with_name("import_photos.py")

# ログ/返却の末尾サイズ（重いログで詰まらないように）
LOG_TAIL = 2000
RET_TAIL = 20000

# MCPのタイムアウトより短くする（MCPがタイムアウトすると情報が消えるので）
SUBPROCESS_TIMEOUT_SEC = 50


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str) -> None:
    sys.stderr.write(f"[{_ts()}] {msg}\n")
    sys.stderr.flush()


def _tail(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    return s[-n:]

def _viewer_url(root_path: str) -> str:
    base = "https://photoviewer.web.app/main.html#"
    rp = root_path.strip().strip("/")
    if rp:
        return f"{base}/{rp}"
    return f"{base}/"


@mcp.tool()
def import_photos(
    input_dir: str,
    root_path: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    req_id = str(int(time.time() * 1000))
    t0 = time.time()

    _log(f"[MCP][{req_id}] import_photos START")
    _log(
        f"[MCP][{req_id}] args input_dir={input_dir!r} "
        f"root_path={root_path!r} dry_run={dry_run!r}"
    )
    _log(f"[MCP][{req_id}] cwd={os.getcwd()!r}")
    _log(f"[MCP][{req_id}] sys.executable={sys.executable!r}")
    _log(f"[MCP][{req_id}] SCRIPT_PATH={str(SCRIPT_PATH)!r} exists={SCRIPT_PATH.exists()}")

    # 入力バリデーション（ここで落ちると一瞬で返る）
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        _log(f"[MCP][{req_id}] ERROR input_dir not found or not dir: {input_dir!r}")
        return {
            "ok": False,
            "error": f"input_dir not found or not a directory: {input_dir!r}",
            "hint": "Windowsなら C:/Users/... のように指定してください",
        }

    if not SCRIPT_PATH.exists():
        _log(f"[MCP][{req_id}] ERROR import_photos.py not found at {SCRIPT_PATH}")
        return {"ok": False, "error": f"import_photos.py not found at {SCRIPT_PATH}"}

    # コマンド組み立て
    
    # cmd = [sys.executable, "-S", "-c", "import sys; sys.stderr.write('[no-site] OK\\n'); sys.stderr.flush(); sys.exit(0)"]
    cmd = [sys.executable, str(SCRIPT_PATH), "--input-dir", input_dir]

    # cmd = [sys.executable, str(SCRIPT_PATH), "--input-dir", str(input_path)]
    if root_path:
        cmd += ["--root-path", root_path]
    if dry_run:
        cmd += ["--dry-run"]

    _log(f"[MCP][{req_id}] cmd={cmd}")

    # env（import_photos.py の print を捕捉しやすく）
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        cp = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=SUBPROCESS_TIMEOUT_SEC,
        )

        dt = time.time() - t0
        _log(f"[MCP][{req_id}] subprocess DONE rc={cp.returncode} elapsed={dt:.2f}s")
        _log(f"[MCP][{req_id}] stdout(last{LOG_TAIL}):\n{_tail(cp.stdout, LOG_TAIL)}")
        _log(f"[MCP][{req_id}] stderr(last{LOG_TAIL}):\n{_tail(cp.stderr, LOG_TAIL)}")

        return {
            "ok": cp.returncode == 0,
            "exit_code": cp.returncode,
            "command": cmd,
            "elapsed_sec": round(dt, 3),
            "stdout": _tail(cp.stdout, RET_TAIL),
            "stderr": _tail(cp.stderr, RET_TAIL),
            "viewer_url": _viewer_url(root_path),
        }

    except subprocess.TimeoutExpired as e:
        dt = time.time() - t0
        # TimeoutExpired でも部分出力を持っている場合がある
        out = getattr(e, "stdout", None)
        err = getattr(e, "stderr", None)

        _log(f"[MCP][{req_id}] TIMEOUT elapsed={dt:.2f}s (>{SUBPROCESS_TIMEOUT_SEC}s)")
        _log(f"[MCP][{req_id}] TIMEOUT cmd={cmd}")
        if out or err:
            _log(f"[MCP][{req_id}] timeout stdout(last{LOG_TAIL}):\n{_tail(out, LOG_TAIL)}")
            _log(f"[MCP][{req_id}] timeout stderr(last{LOG_TAIL}):\n{_tail(err, LOG_TAIL)}")

        return {
            "ok": False,
            "error": f"subprocess timeout (> {SUBPROCESS_TIMEOUT_SEC}s)",
            "command": cmd,
            "elapsed_sec": round(dt, 3),
            "stdout": _tail(out, RET_TAIL),
            "stderr": _tail(err, RET_TAIL),
        }

    except Exception:
        dt = time.time() - t0
        _log(f"[MCP][{req_id}] EXCEPTION elapsed={dt:.2f}s")
        _log(traceback.format_exc())
        return {
            "ok": False,
            "error": "exception in server.py",
            "elapsed_sec": round(dt, 3),
        }


@mcp.tool()
def ping() -> dict:
    _log("[MCP] ping")
    return {"ok": True}


@mcp.tool()
def debug_info() -> dict:
    return {
        "ok": True,
        "server_py": str(Path(__file__).resolve()),
        "cwd": os.getcwd(),
        "sys_executable": sys.executable,
        "script_path": str(SCRIPT_PATH.resolve()),
        "script_exists": SCRIPT_PATH.exists(),
    }


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "http":
        transport = "streamable-http"
    if transport in {"sse", "streamable-http"}:
        _log(f"[MCP] server starting ({transport}) http://{HOST}:{PORT}")
        mcp.run(transport=transport)
    else:
        _log("[MCP] server starting (stdio)")
        mcp.run(transport="stdio")
