import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

let cached: Client | null = null;

export async function getMcpClient() {
  if (cached) return cached;

  const url = process.env.MCP_SERVER_URL ?? "http://127.0.0.1:8000/sse";
  const transport = new SSEClientTransport(new URL(url));

  const client = new Client({ name: "mcp-gemini-chat", version: "0.1.0" });
  await client.connect(transport);

  cached = client;
  return client;
}
