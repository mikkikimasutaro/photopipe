import crypto from "crypto";
import { NextResponse } from "next/server";
import { getRtdb } from "@/lib/firebaseAdmin";

export const runtime = "nodejs";

type InviteRequest = {
  ownerId: string;
  displayName?: string;
  ttlMinutes?: number;
};

export async function POST(req: Request) {
  try {
    const secret = process.env.PAIRING_SECRET ?? process.env.pairing_secret;
    if (!secret) {
      return NextResponse.json({ error: "Missing PAIRING_SECRET" }, { status: 500 });
    }

    const header = req.headers.get("x-pairing-secret");
    if (header !== secret) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const payload = (await req.json()) as InviteRequest;
    if (!payload.ownerId) {
      return NextResponse.json({ error: "ownerId is required" }, { status: 400 });
    }

    const ttlMinutes = payload.ttlMinutes ?? 10;
    const inviteId = crypto.randomUUID();
    const now = Date.now();
    const invite = {
      ownerId: payload.ownerId,
      displayName: payload.displayName ?? null,
      createdAt: now,
      expiresAt: now + ttlMinutes * 60_000,
      status: "pending",
    };

    await getRtdb().ref(`device_invites/${inviteId}`).set(invite);
    return NextResponse.json({ inviteId, expiresAt: invite.expiresAt });
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message ?? String(e) },
      { status: 500 }
    );
  }
}
