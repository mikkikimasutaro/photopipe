# Photo Viewer

A web application for viewing photos, built with Node.js and Firebase.


## Uses Scripts

sudo mount -t cifs //landisk-0c2790.local/disk1 /mnt/landisk -o guest,iocharset=utf8

source scripts/.venv/bin/activate

python3 scripts/import_photos.py --input-dir /mnt/landisk/Pictures/2014-02-03-samplephotos　新婚旅衁E --root-path samplephotos


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
python ./scripts/server.py
```

mcp-client/run_mcp.sh (starts Next.js client):
```sh
export GEMINI_API_KEY="YOUR_KEY"
npm run dev
```
