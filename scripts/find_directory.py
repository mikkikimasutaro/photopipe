#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


IMAGE_EXTS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp", ".tiff", ".tif"
}
VIDEO_EXTS: Set[str] = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".mts", ".m2ts"
}
MEDIA_EXTS: Set[str] = IMAGE_EXTS | VIDEO_EXTS

DEFAULT_SKIP_DIRNAMES: Set[str] = {
    "$recycle.bin", "system volume information",
    "windows", "program files", "program files (x86)",
    "node_modules", ".git", ".svn", ".hg",
    "venv", ".venv", "__pycache__",
}

# ==== 環境変数 ====
MAX_KEYWORD_DIRS = int(os.getenv("MAX_KEYWORD_DIRS", "50"))
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "20000"))


def is_hidden_like(p: Path) -> bool:
    return p.name.startswith(".")


def default_roots() -> List[Path]:
    home = Path.home()
    roots = [
        home,
        home / "Pictures",
        home / "Desktop",
        home / "Downloads",
        home / "OneDrive",
    ]

    uniq: List[Path] = []
    seen = set()
    for r in roots:
        if r.exists():
            rp = r.resolve()
            if str(rp) not in seen:
                uniq.append(rp)
                seen.add(str(rp))
    return uniq


def find_keyword_dirs(
    roots: List[Path],
    keyword: str,
    include_hidden: bool,
    skip_dirnames: Set[str],
) -> List[Path]:
    keyword_lower = keyword.lower()
    hits: List[Path] = []

    for root in roots:
        for dirpath, dirnames, _ in os.walk(root, followlinks=False):
            cur = Path(dirpath)

            filtered = []
            for d in dirnames:
                dp = cur / d
                if d.lower() in skip_dirnames:
                    continue
                if not include_hidden and is_hidden_like(dp):
                    continue
                filtered.append(d)
            dirnames[:] = filtered

            if keyword_lower in str(cur).lower():
                hits.append(cur)
                if len(hits) >= MAX_KEYWORD_DIRS:
                    return hits

    return hits


def count_media_by_directory(
    dirs: List[Path],
    include_hidden: bool,
    skip_dirnames: Set[str],
) -> Dict[Path, int]:
    counts: Dict[Path, int] = defaultdict(int)
    total_media = 0

    for base in dirs:
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            cur = Path(dirpath)

            filtered = []
            for d in dirnames:
                dp = cur / d
                if d.lower() in skip_dirnames:
                    continue
                if not include_hidden and is_hidden_like(dp):
                    continue
                filtered.append(d)
            dirnames[:] = filtered

            for fn in filenames:
                fp = cur / fn
                if not include_hidden and is_hidden_like(fp):
                    continue
                if fp.suffix.lower() in MEDIA_EXTS:
                    counts[cur] += 1
                    total_media += 1
                    if total_media >= MAX_IMAGES:
                        return counts

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count images per directory by forcing a directory keyword."
    )
    parser.add_argument("--keyword", required=True, help="Directory keyword (e.g. DCIM, Pictures)")
    parser.add_argument("--roots", nargs="*", default=[], help="Optional search roots")
    parser.add_argument("--include-hidden", action="store_true", help="Include dot files/dirs")
    parser.add_argument("--no-default-skip", action="store_true", help="Do not skip common system dirs")
    args = parser.parse_args()

    skip = set() if args.no_default_skip else set(DEFAULT_SKIP_DIRNAMES)
    roots = [Path(r).expanduser().resolve() for r in args.roots] if args.roots else default_roots()
    roots = [r for r in roots if r.exists()]

    print(f"[INFO] MAX_KEYWORD_DIRS={MAX_KEYWORD_DIRS}, MAX_IMAGES={MAX_IMAGES}")

    keyword_dirs = find_keyword_dirs(
        roots=roots,
        keyword=args.keyword,
        include_hidden=args.include_hidden,
        skip_dirnames=skip,
    )

    if not keyword_dirs:
        print(f'[INFO] No directories matched keyword="{args.keyword}"')
        return 0

    print(f'[INFO] Matched {len(keyword_dirs)} directories by keyword="{args.keyword}"')

    counts = count_media_by_directory(
        dirs=keyword_dirs,
        include_hidden=args.include_hidden,
        skip_dirnames=skip,
    )

    if not counts:
        print("[RESULT] No media files found.")
        return 0

    print("\n[RESULT] Media file count by directory:")
    total = 0
    for d, c in sorted(counts.items(), key=lambda x: x[0]):
        print(f"{d} : {c}")
        total += c

    print(f"\n[SUMMARY] Total media files counted: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
