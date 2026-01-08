import fs from "fs";
import path from "path";
import { Readable } from "stream";

export const runtime = "nodejs";

const MIME_BY_EXT: Record<string, string> = {
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
};

function getMimeType(filePath: string) {
  const ext = path.extname(filePath).toLowerCase();
  return MIME_BY_EXT[ext] ?? "application/octet-stream";
}

function parseRange(rangeHeader: string | null, size: number) {
  if (!rangeHeader) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(rangeHeader);
  if (!match) return null;

  const startStr = match[1];
  const endStr = match[2];
  let start = startStr ? Number(startStr) : 0;
  let end = endStr ? Number(endStr) : size - 1;

  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  if (!startStr && endStr) {
    const suffix = Number(endStr);
    if (Number.isNaN(suffix) || suffix <= 0) return null;
    start = Math.max(size - suffix, 0);
    end = size - 1;
  }
  if (start < 0) return null;
  if (end >= size) end = size - 1;
  if (start > end || start >= size) return null;

  return { start, end };
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const filePath = url.searchParams.get("path");
  if (!filePath) {
    return new Response("Missing path", { status: 400 });
  }

  const resolved = path.resolve(filePath);
  let stat: fs.Stats;
  try {
    stat = await fs.promises.stat(resolved);
  } catch {
    return new Response("Not found", { status: 404 });
  }

  if (!stat.isFile()) {
    return new Response("Not a file", { status: 404 });
  }

  const range = parseRange(req.headers.get("range"), stat.size);
  const mime = getMimeType(resolved);
  const headers = new Headers({
    "content-type": mime,
    "accept-ranges": "bytes",
    "cache-control": "no-store",
  });

  if (range) {
    const { start, end } = range;
    const stream = fs.createReadStream(resolved, { start, end });
    headers.set("content-length", String(end - start + 1));
    headers.set("content-range", `bytes ${start}-${end}/${stat.size}`);
    return new Response(Readable.toWeb(stream) as ReadableStream, {
      status: 206,
      headers,
    });
  }

  const stream = fs.createReadStream(resolved);
  headers.set("content-length", String(stat.size));
  return new Response(Readable.toWeb(stream) as ReadableStream, { status: 200, headers });
}
