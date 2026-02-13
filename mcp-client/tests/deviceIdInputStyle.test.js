const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const filePath = path.join(__dirname, "..", "app", "page.tsx");
const contents = fs.readFileSync(filePath, "utf8");

test("deviceId input text is forced to dark color", () => {
  assert.match(contents, /\.device-row input/);
  assert.match(contents, /color:\s*#111/);
  assert.match(contents, /-webkit-text-fill-color:\s*#111/);
});
