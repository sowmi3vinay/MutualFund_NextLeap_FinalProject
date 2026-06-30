# Deployment Guide

This project is ready for a split deployment:

- Backend: FastAPI on Render, Railway, Fly.io, or any Python web service
- Frontend: Vite static site on Vercel, Netlify, or Render static sites
- Production vector storage: Supabase Postgres with pgvector
- Local fallback vector storage: ChromaDB under `data/vector_store/`

Current deployment status:

- codebase is deployment-prepared
- backend / frontend env wiring exists
- Supabase adapter exists
- Google Sheets logging exists
- final hosted deployment is still pending

## Backend

Recommended first deployment target: Render web service.

1. Create a new Python web service from the project repository.
2. Use these commands:

```bash
pip install -r apps/api/requirements-render.txt
cd apps/api && uvicorn main:app --host 0.0.0.0 --port $PORT
```

Use Python `3.11.9` for the backend service. The repo now includes both `render.yaml` and `.python-version` to keep Render away from Python 3.14, which was pulling an oversized CUDA-enabled `torch` stack and causing out-of-memory failures during deploy.

3. Set environment variables:

```text
APP_ENV=production
GROQ_API_KEY=<your Groq key>
CORS_ORIGINS=<frontend production URL>
EMBEDDING_LOCAL_FILES_ONLY=false
VECTOR_BACKEND=supabase
SUPABASE_URL=<project URL>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
SUPABASE_DB_PASSWORD=<database password>
SUPABASE_VECTOR_TABLE=document_chunks
GOOGLE_SERVICE_ACCOUNT_JSON=<service-account JSON blob>
GOOGLE_SHEETS_BOOKING_SPREADSHEET_ID=<sheet id>
GOOGLE_SHEETS_BOOKING_WORKSHEET=Bookings
```

`EMBEDDING_LOCAL_FILES_ONLY=false` allows the server to download `sentence-transformers/all-MiniLM-L6-v2` on first boot. Keep it `true` only when the model is already cached on the deployment machine.

If you deploy on Render, prefer the repo `render.yaml` values for:

```text
PYTHON_VERSION=3.11.9
VECTOR_BACKEND=supabase
```

4. Confirm the backend is live:

```bash
curl https://<backend-url>/health
```

Expected response:

```json
{"status":"ok"}
```

## Frontend

Recommended first deployment target: Vercel or Netlify.

1. Set the project root to `apps/web`.
2. Use:

```bash
npm install
npm run build
```

3. Publish directory:

```text
dist
```

4. Set environment variables:

```text
VITE_API_BASE_URL=https://<backend-url>
VITE_VAPI_PUBLIC_KEY=<Vapi public key>
VITE_VAPI_ASSISTANT_ID=<Vapi assistant ID>
```

5. After the frontend URL is created, add it to backend `CORS_ORIGINS`.

## Vector Storage

Production should use Supabase pgvector. Run `supabase/migrations/001_create_document_chunks.sql` in Supabase SQL Editor, then ingest chunks with `VECTOR_BACKEND=supabase`.

Local development can still use the ChromaDB files in `data/vector_store/` plus the processed chunks in `data/sources/processed/source_chunks.jsonl` by setting:

```text
VECTOR_BACKEND=chroma
```

## Supabase pgvector Migration

For Supabase pgvector:

1. Create a Supabase project.
2. Enable the `vector` extension.
3. Run `supabase/migrations/001_create_document_chunks.sql`.
4. Re-ingest source chunks into Supabase.
5. Update backend env vars:

```text
VECTOR_BACKEND=supabase
SUPABASE_URL=<project URL>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
SUPABASE_DB_PASSWORD=<database password>
SUPABASE_VECTOR_TABLE=document_chunks
```

6. Rebuild the production vector store:

```bash
cd "/Users/vinay.paravastu/Downloads/personal projects/Final graduation project"
apps/api/.venv/bin/python scripts/refresh_vector_store.py
```

## Google Sheets Setup

If you want approved bookings logged in production:

1. Share the target Google Sheet with the service-account email.
2. Set:

```text
GOOGLE_SERVICE_ACCOUNT_JSON=<entire JSON as a secret>
GOOGLE_SHEETS_BOOKING_SPREADSHEET_ID=<sheet id>
GOOGLE_SHEETS_BOOKING_WORKSHEET=Bookings
```

Notes:

- use `GOOGLE_SERVICE_ACCOUNT_JSON` in deployment
- keep `GOOGLE_SERVICE_ACCOUNT_FILE` for local development only
- logging happens after MCP approval, not directly from the voice scheduler

## Local Production Check

From `apps/api`:

```bash
source .venv/bin/activate
EMBEDDING_LOCAL_FILES_ONLY=true uvicorn main:app --port 8000
```

From `apps/web`:

```bash
npm run build
npm run preview
```

## Recommended Final Deploy Sequence

1. Deploy backend
2. Set backend env vars
3. Configure Supabase and ingest vectors
4. Verify `/health`, `/faq/ask`, and `/scheduler/greeting`
5. Deploy frontend
6. Set `VITE_API_BASE_URL` and Vapi env vars
7. Add frontend URL to backend `CORS_ORIGINS`
8. Verify:
   - FAQ responses
   - Weekly Pulse generation
   - Vapi call flow
   - Approval Centre
   - Google Sheets logging after approval
