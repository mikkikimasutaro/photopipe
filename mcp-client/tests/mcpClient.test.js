const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const filePath = path.join(__dirname, "..", "lib", "mcpClient.ts");
const contents = fs.readFileSync(filePath, "utf8");

test("mcpClient requires deviceId when MCP_TRANSPORT=rtdb", () => {
  assert.match(contents, /MCP_TRANSPORT/);
  assert.match(contents, /rtdb/);
  assert.match(contents, /deviceId is required when MCP_TRANSPORT=rtdb/);
});

test("mcpClient defaults to local SSE URL", () => {
  assert.match(contents, /http:\/\/127\.0\.0\.1:8000\/sse/);
});
