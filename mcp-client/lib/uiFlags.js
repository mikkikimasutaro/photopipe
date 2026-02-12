const SHOW_IMPORT_JOBS_ENV = "NEXT_PUBLIC_SHOW_IMPORT_JOBS";

function shouldShowImportJobs() {
  return process.env[SHOW_IMPORT_JOBS_ENV] === "true";
}

module.exports = {
  SHOW_IMPORT_JOBS_ENV,
  shouldShowImportJobs,
};
