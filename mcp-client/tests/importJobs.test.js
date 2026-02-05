const test = require("node:test");
const assert = require("node:assert");

const { normalizeRootPath, formatImportJob } = require("../lib/importJobs.js");

test("normalizeRootPath adds leading slash and trims trailing", () => {
  assert.strictEqual(normalizeRootPath("samplephotos"), "/samplephotos");
  assert.strictEqual(normalizeRootPath("/samplephotos/"), "/samplephotos");
  assert.strictEqual(normalizeRootPath(""), "/");
});

test("formatImportJob keeps inputDir and normalized rootPath", () => {
  const job = formatImportJob({
    inputDir: "C:/Users/demo/Pictures",
    rootPath: "samplephotos",
    status: "queued",
    jobId: "job-1",
  });

  assert.strictEqual(job.inputDir, "C:/Users/demo/Pictures");
  assert.strictEqual(job.rootPath, "/samplephotos");
  assert.ok(job.title.includes("C:/Users/demo/Pictures"));
  assert.ok(job.title.includes("/samplephotos"));
});
