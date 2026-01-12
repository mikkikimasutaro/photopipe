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
FIND_SCRIPT_PATH = Path(__file__).with_name("find_directory.py")
LIST_MEDIA_PATH = Path(__file__).with_name("list_media.py")

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp", ".tiff", ".tif"
}
VIDEO_EXTS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".mts", ".m2ts"
}
MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heic",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".webm": "video/webm",
    ".mts": "video/mp2t",
    ".m2ts": "video/mp2t",
}

# ログ/返却の末尾サイズ（重いログで詰まらないように）
LOG_TAIL = 2000
RET_TAIL = 20000

# MCPのタイムアウトより短くする（MCPがタイムアウトすると情報が消えるので）
SUBPROCESS_TIMEOUT_SEC = 120


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str) -> None:
    sys.stderr.write(f"[{_ts()}] {msg}\n")
    sys.stderr.flush()


def _tail(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    return s[-n:]

def _media_kind_and_mime(ext: str) -> tuple[Optional[str], str]:
    el = ext.lower()
    if el in IMAGE_EXTS:
        return "image", MIME_BY_EXT.get(el, "image/*")
    if el in VIDEO_EXTS:
        return "video", MIME_BY_EXT.get(el, "video/*")
    return None, "application/octet-stream"

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
            encoding="utf-8",
            errors="replace",
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
def find_directory(
    keyword: str,
    roots: Optional[list[str]] = None,
    include_hidden: bool = False,
    no_default_skip: bool = False,
) -> Dict[str, Any]:
    req_id = str(int(time.time() * 1000))
    t0 = time.time()

    _log(f"[MCP][{req_id}] find_directory START")
    _log(
        f"[MCP][{req_id}] args keyword={keyword!r} roots={roots!r} "
        f"include_hidden={include_hidden!r} no_default_skip={no_default_skip!r}"
    )
    _log(f"[MCP][{req_id}] cwd={os.getcwd()!r}")
    _log(f"[MCP][{req_id}] sys.executable={sys.executable!r}")
    _log(
        f"[MCP][{req_id}] FIND_SCRIPT_PATH={str(FIND_SCRIPT_PATH)!r} "
        f"exists={FIND_SCRIPT_PATH.exists()}"
    )

    if not keyword or not keyword.strip():
        _log(f"[MCP][{req_id}] ERROR keyword is empty")
        return {"ok": False, "error": "keyword is required"}

    if not FIND_SCRIPT_PATH.exists():
        _log(f"[MCP][{req_id}] ERROR find_directory.py not found at {FIND_SCRIPT_PATH}")
        return {"ok": False, "error": f"find_directory.py not found at {FIND_SCRIPT_PATH}"}

    cmd = [sys.executable, str(FIND_SCRIPT_PATH), "--keyword", keyword]
    if roots:
        cmd += ["--roots", *roots]
    if include_hidden:
        cmd += ["--include-hidden"]
    if no_default_skip:
        cmd += ["--no-default-skip"]

    _log(f"[MCP][{req_id}] cmd={cmd}")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

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
        }

    except subprocess.TimeoutExpired as e:
        dt = time.time() - t0
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
        "find_script_path": str(FIND_SCRIPT_PATH.resolve()),
        "find_script_exists": FIND_SCRIPT_PATH.exists(),
        "list_media_path": str(LIST_MEDIA_PATH.resolve()),
        "list_media_exists": LIST_MEDIA_PATH.exists(),
    }


@mcp.tool()
def get_media(
    file_path: str,
) -> Dict[str, Any]:
    req_id = str(int(time.time() * 1000))
    _log(f"[MCP][{req_id}] get_media START")
    _log(f"[MCP][{req_id}] args file_path={file_path!r}")
    _log(f"[MCP][{req_id}] cwd={os.getcwd()!r}")
    _log(f"[MCP][{req_id}] sys.executable={sys.executable!r}")

    if not file_path or not file_path.strip():
        _log(f"[MCP][{req_id}] ERROR file_path is empty")
        return {"ok": False, "error": "file_path is required"}

    p = Path(file_path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        _log(f"[MCP][{req_id}] ERROR file not found: {file_path!r}")
        return {"ok": False, "error": f"file not found or not a file: {file_path!r}"}

    kind, mime = _media_kind_and_mime(p.suffix)
    if not kind:
        _log(f"[MCP][{req_id}] ERROR unsupported extension: {p.suffix!r}")
        return {"ok": False, "error": f"unsupported media type: {p.suffix!r}"}

    size_bytes = p.stat().st_size
    return {
        "ok": True,
        "media_path": str(p),
        "media_type": kind,
        "mime_type": mime,
        "file_name": p.name,
        "size_bytes": size_bytes,
        "path": str(p),
        "type": kind,
        "mime": mime,
        "name": p.name,
    }


@mcp.tool()
def list_media(
    dir_path: str,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    req_id = str(int(time.time() * 1000))
    t0 = time.time()

    _log(f"[MCP][{req_id}] list_media START")
    _log(f"[MCP][{req_id}] args dir_path={dir_path!r} include_hidden={include_hidden!r}")
    _log(f"[MCP][{req_id}] cwd={os.getcwd()!r}")
    _log(f"[MCP][{req_id}] sys.executable={sys.executable!r}")
    _log(
        f"[MCP][{req_id}] LIST_MEDIA_PATH={str(LIST_MEDIA_PATH)!r} "
        f"exists={LIST_MEDIA_PATH.exists()}"
    )

    if not dir_path or not dir_path.strip():
        _log(f"[MCP][{req_id}] ERROR dir_path is empty")
        return {"ok": False, "error": "dir_path is required"}

    if not LIST_MEDIA_PATH.exists():
        _log(f"[MCP][{req_id}] ERROR list_media.py not found at {LIST_MEDIA_PATH}")
        return {"ok": False, "error": f"list_media.py not found at {LIST_MEDIA_PATH}"}

    cmd = [sys.executable, str(LIST_MEDIA_PATH), "--dir", dir_path]
    if include_hidden:
        cmd += ["--include-hidden"]

    _log(f"[MCP][{req_id}] cmd={cmd}")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

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
        }

    except subprocess.TimeoutExpired as e:
        dt = time.time() - t0
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
