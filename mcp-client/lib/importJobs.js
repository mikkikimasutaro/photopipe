function normalizeRootPath(rootPath) {
  if (!rootPath) return "/";
  let cleaned = String(rootPath).trim().replace(/\\/g, "/");
  if (!cleaned.startsWith("/")) cleaned = `/${cleaned}`;
  cleaned = cleaned.replace(/\/+$/, "");
  return cleaned || "/";
}

function formatImportJob(job) {
  const normalized = normalizeRootPath(job.rootPath || "");
  const inputDir = job.inputDir || "";
  return {
    ...job,
    inputDir,
    rootPath: normalized,
    title: `${inputDir} -> ${normalized}`.trim(),
  };
}

module.exports = { normalizeRootPath, formatImportJob };
