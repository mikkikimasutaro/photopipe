#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, List, Set

IMAGE_EXTS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp", ".tiff", ".tif"
}
VIDEO_EXTS: Set[str] = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".mts", ".m2ts"
}

MAX_FILES = int(os.getenv("MAX_MEDIA_FILES", "5000"))


def is_hidden_like(p: Path) -> bool:
    return p.name.startswith(".")


def iter_media_files(base: Path, include_hidden: bool) -> Iterable[Path]:
    for p in base.iterdir():
        if not p.is_file():
            continue
        if not include_hidden and is_hidden_like(p):
            continue
        if p.suffix.lower() in IMAGE_EXTS or p.suffix.lower() in VIDEO_EXTS:
            yield p


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # Fallback for older Python or restricted environments.
        pass

    parser = argparse.ArgumentParser(
        description="List image/video files directly under a directory."
    )
    parser.add_argument("--dir", required=True, help="Target directory full path")
    parser.add_argument("--include-hidden", action="store_true", help="Include dot files")
    args = parser.parse_args()

    base = Path(args.dir).expanduser().resolve()
    if not base.exists() or not base.is_dir():
        print(f"[ERROR] dir not found or not a directory: {args.dir!r}")
        return 1

    files: List[Path] = []
    for p in iter_media_files(base, include_hidden=args.include_hidden):
        files.append(p)
        if len(files) >= MAX_FILES:
            break

    print(f"[INFO] MAX_MEDIA_FILES={MAX_FILES}")
    print(f"[INFO] dir={str(base)}")

    if not files:
        print("[RESULT] No media files found.")
        return 0

    print(f"\n[RESULT] Media files ({len(files)}):")
    for p in sorted(files, key=lambda x: x.name.lower()):
        print(str(p))

    print(f"\n[SUMMARY] Total media files listed: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
