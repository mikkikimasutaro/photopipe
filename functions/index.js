const { onRequest } = require("firebase-functions/v2/https");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { PubSub } = require("@google-cloud/pubsub");

initializeApp();

const pubsub = new PubSub();

const IMPORT_JOBS_TOPIC = process.env.IMPORT_JOBS_TOPIC || "photo-import-jobs";
const IMPORT_JOBS_COLLECTION = process.env.IMPORT_JOBS_COLLECTION || "importJobs";
const IMPORT_JOB_SECRET = process.env.IMPORT_JOB_SECRET || "";

function validateBody(body) {
  if (!body || typeof body !== "object") {
    return "body is required";
  }
  if (!body.inputDir || typeof body.inputDir !== "string") {
    return "inputDir is required";
  }
  if (body.rootPath && typeof body.rootPath !== "string") {
    return "rootPath must be a string";
  }
  if (body.dryRun != null && typeof body.dryRun !== "boolean") {
    return "dryRun must be a boolean";
  }
  return null;
}

exports.enqueueImportJob = onRequest(async (req, res) => {
  if (IMPORT_JOB_SECRET) {
    const provided = req.get("x-import-job-secret") || "";
    if (provided !== IMPORT_JOB_SECRET) {
      res.status(403).json({ ok: false, error: "invalid secret" });
      return;
    }
  }

  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "method not allowed" });
    return;
  }

  const error = validateBody(req.body);
  if (error) {
    res.status(400).json({ ok: false, error });
    return;
  }

  const db = getFirestore();
  const jobRef = db.collection(IMPORT_JOBS_COLLECTION).doc();
  const jobId = jobRef.id;

  const payload = {
    jobId,
    inputDir: req.body.inputDir,
    rootPath: req.body.rootPath || "",
    dryRun: Boolean(req.body.dryRun),
    requestedBy: req.body.requestedBy || null,
    workerId: req.body.workerId || null,
  };

  await jobRef.set({
    ...payload,
    status: "queued",
    createdAt: FieldValue.serverTimestamp(),
  });

  await pubsub.topic(IMPORT_JOBS_TOPIC).publishMessage({
    json: payload,
  });

  res.json({ ok: true, jobId });
});
