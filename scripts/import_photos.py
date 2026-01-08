#!/usr/bin/env python3
"""
Import a local photo folder structure into Firestore + Firebase Storage.

What it does:
- Walks a local directory, builds folder documents in Firestore.
- Generates and uploads two resized images per photo:
  - thumb: long edge 256px  -> stored at photos/<rel>/thumb/<filename>
  - medium: long edge 1280px -> stored at photos/<rel>/medium/<filename>
- Creates photo documents pointing to the Storage paths.

Expected Firestore schema:
- collection: folders
  { id, name, path, parentPath, order?, createdAt? }
- collection: photos
  { id, fileName, folderPath, thumbPath, mediumPath, width, height,
    capturedAt?, createdAt, order? }

Prereqs (install):
  pip install firebase-admin Pillow

Auth:
- Uses the fixed service account JSON bundled with this repo.
"""

from __future__ import annotations

import argparse
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

import firebase_admin
from firebase_admin import credentials, firestore, storage
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

BASE_DIR = Path(__file__).resolve().parents[1]
SERVICE_ACCOUNT_PATH = BASE_DIR / "mikkikicom-firebase-adminsdk-fbsvc-06bdbf6b0d.json"
STORAGE_BUCKET = "mikkikicom.firebasestorage.app"


def elog(msg: str):
    sys.stderr.write(f"[import_photos] {time.strftime('%H:%M:%S')} {msg}\n")
    sys.stderr.flush()


def parse_args():
    p = argparse.ArgumentParser(description="scan and create lightweight images optimized for viewing on smartphones and upload them to Firebase Storage")
    p.add_argument("--input-dir", required=True, help="Local folder to scan (images only)")
    p.add_argument("--root-path", required=True, help="Virtual root path prefix in Firestore (e.g. /2024)")
    p.add_argument("--dry-run", action="store_true", help="Do not write to Firestore/Storage")
    return p.parse_args()


def init_firebase():
    if not SERVICE_ACCOUNT_PATH.exists():
        raise SystemExit(f"Service account JSON not found: {SERVICE_ACCOUNT_PATH}")
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
    firebase_admin.initialize_app(cred, {"storageBucket": STORAGE_BUCKET})
    return firestore.client(), storage.bucket()


def is_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}


def resize_image(src_path: Path, long_edge: int) -> Tuple[BytesIO, Tuple[int, int]]:
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return buf, im.size


def normalize_path(path: str) -> str:
    if not path:
        return ""
    path = path.replace("\\", "/")
    if not path.startswith("/"):
        path = "/" + path
    path = path.replace("//", "/")
    return path.rstrip("/") or ""


def validate_virtual_root(root_path: str):
    # Prevent accidentally using a local absolute path like C:/...
    lowered = root_path.lower()
    if ":" in root_path.split("/")[0]:
        raise SystemExit(
            f"--root-path looks like a local path ('{root_path}'). "
            "Use a virtual path such as '' or '/2024/Trip'."
        )
    if lowered.startswith("c:/") or lowered.startswith("d:/"):
        raise SystemExit(
            f"--root-path looks like a local path ('{root_path}'). "
            "Use a virtual path such as '' or '/2024/Trip'."
        )


def ensure_folder_docs(db, folders: List[Dict], dry_run: bool):
    for f in folders:
        doc_id = f["path"].lstrip("/").replace("/", "_") or "root"
        data = {
            "name": f["name"],
            "path": f["path"],
            "parentPath": f["parentPath"],
            "order": f["order"],
            "createdAt": firestore.SERVER_TIMESTAMP,
        }
        if dry_run:
            print(f"[DRY-RUN] folder doc -> folders/{doc_id} {data}")
        else:
            db.collection("folders").document(doc_id).set(data, merge=True)


def upload_and_make_docs(
    db,
    bucket,
    items: List[Tuple[Path, str, int]],
    root_path: str,
    dry_run: bool,
):
    """
    items: list of (file_path, rel_dir, order)
    """
    for file_path, rel_dir, order in items:
        folder_path = normalize_path("/".join([part for part in [root_path.strip("/"), rel_dir.replace("\\", "/")] if part]))
        parent_path = normalize_path("/".join(folder_path.split("/")[:-1])) if folder_path else ""
        file_name = file_path.name
        jpg_file_name = file_path.stem + ".jpg"
        doc_id = (folder_path.lstrip("/").replace("/", "_") + "_" + file_path.stem).strip("_") or file_path.stem

        # Skip if photo doc already exists
        if not dry_run and db.collection("photos").document(doc_id).get().exists:
            print(f"Skipping {file_name}, already exists.")
            continue

        thumb_rel = "/".join([p for p in ["photos", root_path.strip("/"), rel_dir.replace("\\", "/"), "thumb", jpg_file_name] if p])
        medium_rel = "/".join([p for p in ["photos", root_path.strip("/"), rel_dir.replace("\\", "/"), "medium", jpg_file_name] if p])

        # Resize
        thumb_buf, thumb_size = resize_image(file_path, 256)
        medium_buf, medium_size = resize_image(file_path, 1280)

        if dry_run:
            print(f"[DRY-RUN] upload thumb -> {thumb_rel} size {thumb_size}")
            print(f"[DRY-RUN] upload medium -> {medium_rel} size {medium_size}")
        else:
            thumb_blob = bucket.blob(thumb_rel)
            thumb_blob.upload_from_file(thumb_buf, content_type="image/jpeg")
            medium_blob = bucket.blob(medium_rel)
            medium_blob.upload_from_file(medium_buf, content_type="image/jpeg")

        data = {
            "fileName": file_name,
            "folderPath": folder_path,
            "thumbPath": thumb_rel,
            "mediumPath": medium_rel,
            "width": medium_size[0],
            "height": medium_size[1],
            "capturedAt": None,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "order": order,
        }
        if dry_run:
            print(f"[DRY-RUN] photo doc -> photos/{doc_id} {data}")
        else:
            db.collection("photos").document(doc_id).set(data, merge=True)


def collect_items(base: Path) -> List[Tuple[Path, str]]:
    items = []
    for path in sorted(base.rglob("*")):
        if path.is_file() and is_image(path):
            rel_dir = str(path.parent.relative_to(base)).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            items.append((path, rel_dir))
    return items


def collect_folders(items: List[Tuple[Path, str]], root_path: str) -> List[Dict]:
    seen = set()
    folders: List[Dict] = []
    for _, rel_dir in items:
        parts = [p for p in rel_dir.split("/") if p]
        for i in range(len(parts) + 1):
            sub_parts = parts[: i + 1]
            if not sub_parts:
                folder_path = normalize_path(root_path)
                name = folder_path.rsplit("/", 1)[-1] or "root"
            else:
                folder_path = normalize_path("/".join([root_path.strip("/")] + sub_parts))
                name = sub_parts[-1]
            if folder_path in seen:
                continue
            seen.add(folder_path)
            parent_path = normalize_path("/".join(folder_path.split("/")[:-1])) if folder_path else ""
            folders.append(
                {
                    "name": name,
                    "path": folder_path,
                    "parentPath": parent_path,
                    "order": i,  # shallow depth first; adjust as needed
                }
            )
    return folders

def main():
    args = parse_args()
    elog(f"start argv={sys.argv!r}")
    elog(f"args input_dir={args.input_dir!r} root_path={args.root_path!r} dry_run={args.dry_run!r}")

    validate_virtual_root(args.root_path)
    base = Path(args.input_dir).expanduser().resolve()
    elog(f"resolved base={str(base)!r} exists={base.exists()} is_dir={base.is_dir()}")

    if not base.exists():
        raise SystemExit(f"Input dir not found: {base}")

    print(f"Scanning images under: {base}")
    print(f"Virtual root path    : '{normalize_path(args.root_path)}'")
    elog("collect_items begin")
    items = collect_items(base)
    elog(f"collect_items done count={len(items)}")

    if not items:
        print("No images found.")
        return

    folders = collect_folders(items, args.root_path)

    if args.dry_run:
        db = bucket = None
    else:
        db, bucket = init_firebase()

    ensure_folder_docs(db, folders, args.dry_run)

    # order photos by filename within each folder
    grouped: Dict[str, List[Tuple[Path, str]]] = {}
    for path, rel_dir in items:
        grouped.setdefault(rel_dir, []).append((path, rel_dir))
    ordered_items: List[Tuple[Path, str, int]] = []
    for rel_dir, lst in grouped.items():
        for idx, (path, _) in enumerate(sorted(lst, key=lambda t: t[0].name)):
            ordered_items.append((path, rel_dir, idx))

    upload_and_make_docs(db, bucket, ordered_items, args.root_path, args.dry_run)
    print("Done.")

if __name__ == "__main__":
    main()
