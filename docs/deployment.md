# Deployment Guide

This project is ready for a split deployment:

- Backend: FastAPI on Render, Railway, Fly.io, or any Python web service.
- Frontend: Vite static site on Vercel, Netlify, or Render static sites.
- Deployment vector storage: Supabase Postgres with pgvector.
- Local fallback vector storage: committed/local ChromaDB under `data/vector_store/`.

## Backend

Recommended first deployment target: Render web service.

1. Create a new Python web service from the project repository.
2. Use these commands:

```bash
pip install -r apps/api/requirements.txt
cd apps/api && uvicorn main:app --host 0.0.0.0 --port $PORT
```

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
```

`EMBEDDING_LOCAL_FILES_ONLY=false` allows the server to download `sentence-transformers/all-MiniLM-L6-v2` on first boot. Keep it `true` only when the model is already cached on the deployment machine.

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

4. Set environment variable:

```text
VITE_API_BASE_URL=https://<backend-url>
VITE_VAPI_PUBLIC_KEY=<Vapi public key>
VITE_VAPI_ASSISTANT_ID=<Vapi assistant ID>
```

5. After the frontend URL is created, add it to backend `CORS_ORIGINS`.

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

## Vector Storage

Deployment should use Supabase pgvector. Run `supabase/migrations/001_create_document_chunks.sql` in Supabase SQL Editor, then ingest chunks with `VECTOR_BACKEND=supabase`.

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
