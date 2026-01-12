import crypto from "crypto";
import type { DatabaseReference } from "firebase-admin/database";
import { getRtdb } from "@/lib/firebaseAdmin";

type ListToolsResult = {
  tools: any[];
  nextCursor?: string;
};

type CallToolResult = {
  content: { type: string; text?: string; [key: string]: unknown }[];
  structuredContent?: Record<string, unknown>;
  isError?: boolean;
  [key: string]: unknown;
};

type CallToolParams = {
  name: string;
  arguments?: Record<string, unknown>;
};

type RtdbResponse = {
  status: "done" | "error";
  result?: CallToolResult;
  error?: { message?: string; [key: string]: unknown };
};

export class RtdbMcpClient {
  private readonly deviceId: string;
  private readonly requesterId: string;
  private readonly timeoutMs: number;

  constructor(deviceId: string, timeoutMs = 60_000) {
    this.deviceId = deviceId;
    this.requesterId = crypto.randomUUID();
    this.timeoutMs = timeoutMs;
  }

  async listTools(_params?: { cursor?: string }): Promise<ListToolsResult> {
    const db = getRtdb();
    const snap = await db.ref(`devices/${this.deviceId}/tools`).get();
    const data = snap.val();
    if (!data?.tools || !Array.isArray(data.tools)) {
      throw new Error(`No tools published for device ${this.deviceId}`);
    }
    return { tools: data.tools, nextCursor: undefined };
  }

  async callTool(
    params: CallToolParams,
    _resultSchema?: unknown,
    _options?: unknown
  ): Promise<CallToolResult> {
    const db = getRtdb();
    const requestRef = db.ref(`devices/${this.deviceId}/requests`).push();
    const requestId = requestRef.key;
    if (!requestId) {
      throw new Error("Failed to allocate request id");
    }

    await requestRef.set({
      name: params.name,
      arguments: params.arguments ?? {},
      status: "pending",
      requesterId: this.requesterId,
      createdAt: Date.now(),
      expiresAt: Date.now() + this.timeoutMs,
    });

    const responseRef = db.ref(`devices/${this.deviceId}/responses/${requestId}`);
    const response = await this.waitForResponse(responseRef, this.timeoutMs);

    if (response.status === "done" && response.result) {
      return response.result;
    }

    const message =
      response.error?.message ??
      `Tool call failed for ${params.name} on device ${this.deviceId}`;
    return {
      content: [{ type: "text", text: message }],
      structuredContent: { error: response.error ?? { message } },
      isError: true,
    };
  }

  private async waitForResponse(
    responseRef: DatabaseReference,
    timeoutMs: number
  ): Promise<RtdbResponse> {
    return new Promise((resolve, reject) => {
      const onValue = (snap: { val: () => RtdbResponse | null }) => {
        const data = snap.val();
        if (!data) return;
        if (data.status === "done" || data.status === "error") {
          cleanup();
          resolve(data);
        }
      };

      const onError = (err: Error) => {
        cleanup();
        reject(err);
      };

      const cleanup = () => {
        clearTimeout(timer);
        responseRef.off("value", onValue);
      };

      const timer = setTimeout(() => {
        cleanup();
        reject(new Error("Timed out waiting for device response"));
      }, timeoutMs);

      responseRef.on("value", onValue, onError);
    });
  }
}
