import fs from "fs";
import {
  applicationDefault,
  cert,
  getApps,
  initializeApp,
} from "firebase-admin/app";
import { getDatabase } from "firebase-admin/database";

type ServiceAccount = {
  projectId?: string;
  clientEmail?: string;
  privateKey?: string;
};

let cachedApp: ReturnType<typeof initializeApp> | null = null;

function loadServiceAccount(): ServiceAccount | null {
  const jsonEnv = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (jsonEnv) {
    return JSON.parse(jsonEnv) as ServiceAccount;
  }

  const pathEnv = process.env.FIREBASE_SERVICE_ACCOUNT_PATH;
  if (pathEnv && fs.existsSync(pathEnv)) {
    const raw = fs.readFileSync(pathEnv, "utf8");
    return JSON.parse(raw) as ServiceAccount;
  }

  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n");
  const projectId = process.env.FIREBASE_PROJECT_ID;
  if (clientEmail && privateKey) {
    return { clientEmail, privateKey, projectId };
  }

  return null;
}

export function getAdminApp() {
  if (cachedApp) return cachedApp;

  const databaseURL = process.env.FIREBASE_DATABASE_URL;
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
      projectId: serviceAccount?.projectId ?? process.env.FIREBASE_PROJECT_ID,
    });
  return cachedApp;
}

export function getRtdb() {
  return getDatabase(getAdminApp());
}
