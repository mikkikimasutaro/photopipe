import fs from "fs";
import {
  applicationDefault,
  cert,
  getApps,
  initializeApp,
} from "firebase-admin/app";
import { getDatabase } from "firebase-admin/database";
import { getFirestore } from "firebase-admin/firestore";

type ServiceAccount = {
  projectId?: string;
  clientEmail?: string;
  privateKey?: string;
};

let cachedApp: ReturnType<typeof initializeApp> | null = null;

function loadServiceAccount(): ServiceAccount | null {
  const jsonEnv =
    process.env.FIREBASE_SERVICE_ACCOUNT_JSON ??
    process.env.firebase_service_account_json;
  if (jsonEnv) {
    return JSON.parse(jsonEnv) as ServiceAccount;
  }

  const pathEnv =
    process.env.FIREBASE_SERVICE_ACCOUNT_PATH ??
    process.env.firebase_service_account_path;
  if (pathEnv && fs.existsSync(pathEnv)) {
    const raw = fs.readFileSync(pathEnv, "utf8");
    return JSON.parse(raw) as ServiceAccount;
  }

  const clientEmail =
    process.env.FIREBASE_CLIENT_EMAIL ?? process.env.firebase_client_email;
  const privateKey = (
    process.env.FIREBASE_PRIVATE_KEY ?? process.env.firebase_private_key
  )?.replace(/\\n/g, "\n");
  const projectId =
    process.env.FIREBASE_PROJECT_ID ?? process.env.firebase_project_id;
  if (clientEmail && privateKey) {
    return { clientEmail, privateKey, projectId };
  }

  return null;
}

export function getAdminApp() {
  if (cachedApp) return cachedApp;

  const databaseURL =
    process.env.FIREBASE_DATABASE_URL ?? process.env.firebase_database_url;
  if (!databaseURL) {
    throw new Error("Missing FIREBASE_DATABASE_URL");
  }

  const serviceAccount = loadServiceAccount();
  const credential = serviceAccount ? cert(serviceAccount) : applicationDefault();

  cachedApp =
    getApps()[0] ??
    initializeApp({
      credential,
      databaseURL,
      projectId:
        serviceAccount?.projectId ??
        process.env.FIREBASE_PROJECT_ID ??
        process.env.firebase_project_id,
    });
  return cachedApp;
}

export function getRtdb() {
  return getDatabase(getAdminApp());
}

export function getFirestoreDb() {
  return getFirestore(getAdminApp());
}
