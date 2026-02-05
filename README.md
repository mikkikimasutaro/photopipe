# Photo Viewer

A web application for viewing photos, built with Node.js and Firebase.


## Uses Scripts

sudo mount -t cifs //landisk-0c2790.local/disk1 /mnt/landisk -o guest,iocharset=utf8

source scripts/.venv/bin/activate

python3 scripts/import_photos.py --input-dir /mnt/landisk/Pictures/2014-02-03-samplephotos　新婚旅衁E --root-path samplephotos

## Import jobs (Cloud Functions + Pub/Sub)

The MCP `import_photos` tool now enqueues a job via a Firebase Cloud Function and
uses Pub/Sub to manage long-running imports. The job unit is **one folder**.

### Components
- Cloud Function: `functions/index.js` -> `enqueueImportJob`
- Pub/Sub topic: default `photo-import-jobs`
- Worker (local PC): `scripts/import_worker.py` subscribes and runs `scripts/import_photos.py`
- Firestore collection: `importJobs/{jobId}` (status: queued/running/done/error)

### Cloud Function setup
```sh
cd functions
npm install
firebase deploy --only functions
```

Environment variables for the Cloud Function:
- `IMPORT_JOBS_TOPIC` (default: `photo-import-jobs`)
- `IMPORT_JOBS_COLLECTION` (default: `importJobs`)
- `IMPORT_JOB_SECRET` (optional; if set, requests must include `x-import-job-secret`)

### MCP server (enqueue)
Required environment variables:
- `IMPORT_JOBS_ENDPOINT` (Cloud Function URL)

Optional:
- `MCP_IMPORT_MODE` (`pubsub` default, set to `local` to run synchronously)
- `IMPORT_JOB_REQUESTER` (free-form string, stored in job doc)
- `IMPORT_JOB_WORKER_ID` (target worker ID for routing)
- `IMPORT_JOB_SECRET` (required if Cloud Function secret is set)

### MCP Client (status UI)
The MCP Client UI shows recent import jobs from Firestore, including:
- import source folder (`inputDir`)
- export path (`rootPath`)
- status (`queued`/`running`/`done`/`error`)

### Worker (executes the job)
Install dependency:
```sh
pip install google-cloud-pubsub firebase-admin Pillow pillow-heif
```

Run the worker:
```sh
export IMPORT_JOBS_SUBSCRIPTION="projects/<project>/subscriptions/<sub>"
export FIREBASE_SERVICE_ACCOUNT_PATH="./your-firebase-adminsdk.json"
python scripts/import_worker.py
```



## Local-only files (not committed)

These files are ignored by git. Create them locally as needed.

Service account JSON (Firebase Admin SDK):
- Place the service account key at repo root as:
  `your-firebase-adminsdk.json`
- Generate it from Firebase console (do not commit it).

server.sh (starts MCP server):
```sh
export MCP_TRANSPORT="sse"
export MCP_HOST="127.0.0.1"
export MCP_PORT="8000"
export MCP_STORAGE_PREFIX="on_demand"
export PAIRING_INVITE_ID="INVITE_ID_FROM_API"
python ./scripts/server.py
```

mcp-client/run_mcp.sh (starts Next.js client):
```sh
export GEMINI_API_KEY="YOUR_KEY"
export MCP_TRANSPORT="rtdb"
export FIREBASE_DATABASE_URL="https://<project>.firebaseio.com"
export PAIRING_SECRET="YOUR_SECRET"
export FIREBASE_SERVICE_ACCOUNT_PATH="../your-firebase-adminsdk.json"
export FIREBASE_PROJECT_ID="your-project-id"
npm run dev
```

Local helper scripts (not committed):

invite_code.sh (create pairing invite):
```sh
export PAIRING_SECRET="YOUR_SECRET"
curl -X POST http://localhost:3000/api/device/invite \
  -H "content-type: application/json" \
  -H "x-pairing-secret: $PAIRING_SECRET" \
  -d '{"ownerId":"local-user","displayName":"My PC"}'
```

rtdb_relay.sh (start RTDB relay):
```sh
export PAIRING_INVITE_ID="INVITE_ID_FROM_API"
export FIREBASE_DATABASE_URL="https://<project>.firebaseio.com"
export FIREBASE_SERVICE_ACCOUNT_PATH="./your-firebase-adminsdk.json"
export FIREBASE_PROJECT_ID="your-project-id"
python scripts/rtdb_relay.py
```

## RTDB relay (remote MCP)

This setup lets the Next.js client use Firebase RTDB to talk to a local MCP server.
The relay runs as a Python script so it can share the same environment as the MCP server.

### App Hosting config (apphosting.yaml)
For App Hosting, use `mcp-client/apphosting.yaml` to declare env vars and secrets.
Secrets referenced in the YAML must be created in App Hosting (Secrets) or Secret Manager.
After creating secrets, grant the App Hosting backend access:
```sh
firebase apphosting:secrets:grantaccess gemini_api_key --backend <BACKEND_NAME>
firebase apphosting:secrets:grantaccess firebase_service_account_json --backend <BACKEND_NAME>
firebase apphosting:secrets:grantaccess pairing_secret --backend <BACKEND_NAME>
```

### Required env (Next.js + relay)
- `FIREBASE_DATABASE_URL`
- one of:
  - `FIREBASE_SERVICE_ACCOUNT_JSON`
  - `FIREBASE_SERVICE_ACCOUNT_PATH`
  - `FIREBASE_CLIENT_EMAIL` + `FIREBASE_PRIVATE_KEY`

### Pairing flow
1) Start MCP server locally:
```sh
export MCP_TRANSPORT="sse"
export MCP_HOST="127.0.0.1"
export MCP_PORT="8000"
export MCP_STORAGE_PREFIX="on_demand"
python ./scripts/server.py
```

2) Start Next.js (set RTDB mode):
```sh
export GEMINI_API_KEY="YOUR_KEY"
npm run dev
```

3) Create invite (server-side API):
```sh
curl -X POST http://localhost:3000/api/device/invite \
  -H "content-type: application/json" \
  -H "x-pairing-secret: $PAIRING_SECRET" \
  -d '{"ownerId":"local-user","displayName":"My PC"}'
```

4) Run the relay on the local PC:
```sh
export PAIRING_INVITE_ID="INVITE_ID_FROM_API"
export FIREBASE_DATABASE_URL="https://<project>.firebaseio.com"
python scripts/rtdb_relay.py
```

5) Put the emitted `deviceId` into the chat UI (Device ID field).

### Notes
- `mcp-client/app/api/media` still reads local file paths on the server. For remote
  viewing, switch to Firebase Storage URLs or add a separate proxy flow.
