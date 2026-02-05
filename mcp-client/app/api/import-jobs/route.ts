import { NextResponse } from "next/server";
import { getFirestoreDb } from "@/lib/firebaseAdmin";

export const runtime = "nodejs";

function toIso(value: any): string | null {
  if (!value) return null;
  if (value.toDate) {
    return value.toDate().toISOString();
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  return null;
}

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const limit = Math.max(1, Math.min(50, Number(searchParams.get("limit")) || 10));

    const db = getFirestoreDb();
    const snap = await db
      .collection("importJobs")
      .orderBy("createdAt", "desc")
      .limit(limit)
      .get();

    const items = snap.docs.map((doc) => {
      const data = doc.data() as Record<string, any>;
      return {
        jobId: data.jobId ?? doc.id,
        status: data.status ?? "unknown",
        inputDir: data.inputDir ?? "",
        rootPath: data.rootPath ?? "",
        requestedBy: data.requestedBy ?? null,
        workerId: data.workerId ?? null,
        createdAt: toIso(data.createdAt),
        startedAt: toIso(data.startedAt),
        finishedAt: toIso(data.finishedAt),
        error: data.error ?? null,
      };
    });

    return NextResponse.json({ items });
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message ?? String(e) },
      { status: 500 }
    );
  }
}
