const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const rootReadme = fs.readFileSync(
  path.join(__dirname, "..", "..", "README.md"),
  "utf8"
);
const pageTsx = fs.readFileSync(
  path.join(__dirname, "..", "app", "page.tsx"),
  "utf8"
);
const layoutTsx = fs.readFileSync(
  path.join(__dirname, "..", "app", "layout.tsx"),
  "utf8"
);

test("README naming includes PhotoPipe and PhotoViewer roles", () => {
  assert.match(rootReadme, /System: PhotoPipe/);
  assert.match(rootReadme, /PhotoPipe Agent/);
  assert.match(rootReadme, /PhotoPipe Client/);
  assert.match(rootReadme, /PhotoViewer/);
});

test("MCP client UI uses PhotoPipe client naming", () => {
  assert.match(pageTsx, /PhotoPipeクライアント/);
  assert.match(layoutTsx, /PhotoPipe Client/);
});
