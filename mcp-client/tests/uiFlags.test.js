const test = require("node:test");
const assert = require("node:assert");

const {
  SHOW_IMPORT_JOBS_ENV,
  shouldShowImportJobs,
} = require("../lib/uiFlags.js");

test("shouldShowImportJobs is false by default", () => {
  const prev = process.env[SHOW_IMPORT_JOBS_ENV];
  delete process.env[SHOW_IMPORT_JOBS_ENV];
  try {
    assert.strictEqual(shouldShowImportJobs(), false);
  } finally {
    if (prev === undefined) {
      delete process.env[SHOW_IMPORT_JOBS_ENV];
    } else {
      process.env[SHOW_IMPORT_JOBS_ENV] = prev;
    }
  }
});

test("shouldShowImportJobs is true when env is 'true'", () => {
  const prev = process.env[SHOW_IMPORT_JOBS_ENV];
  process.env[SHOW_IMPORT_JOBS_ENV] = "true";
  try {
    assert.strictEqual(shouldShowImportJobs(), true);
  } finally {
    if (prev === undefined) {
      delete process.env[SHOW_IMPORT_JOBS_ENV];
    } else {
      process.env[SHOW_IMPORT_JOBS_ENV] = prev;
    }
  }
});
