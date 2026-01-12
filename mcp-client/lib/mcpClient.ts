import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { RtdbMcpClient } from "@/lib/rtdbMcpClient";

type McpClientLike = {
  listTools: (...args: any[]) => Promise<any>;
  callTool: (...args: any[]) => Promise<any>;
};

let cached: Client | null = null;
const cachedRtdb = new Map<string, McpClientLike>();

export async function getMcpClient(deviceId?: string): Promise<McpClientLike> {
  const transportMode = (
    process.env.MCP_TRANSPORT ??
    process.env.mcp_transport ??
    "sse"
  ).toLowerCase();
  if (transportMode === "rtdb") {
    if (!deviceId) {
      throw new Error("deviceId is required when MCP_TRANSPORT=rtdb");
    }
    const existing = cachedRtdb.get(deviceId);
    if (existing) return existing;
    const client = new RtdbMcpClient(deviceId);
    cachedRtdb.set(deviceId, client);
    return client;
  }

  if (cached) return cached;

  const url =
    process.env.MCP_SERVER_URL ??
    process.env.mcp_server_url ??
    "http://127.0.0.1:8000/sse";
  const transport = new SSEClientTransport(new URL(url));

  const client = new Client({ name: "mcp-gemini-chat", version: "0.1.0" });
  await client.connect(transport);

  cached = client;
  return client;
}
