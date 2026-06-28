# Local Runbook

Use this when restarting the local demo after a break.

## 1. Backend

```bash
cd "/Users/vinay.paravastu/Downloads/personal projects/Final graduation project/apps/api"
source .venv/bin/activate
uvicorn main:app --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## 2. Frontend

```bash
cd "/Users/vinay.paravastu/Downloads/personal projects/Final graduation project/apps/web"
source ~/.nvm/nvm.sh
npm run dev
```

Frontend URL is usually:

```text
http://127.0.0.1:5173/
```

If `5173` is occupied, Vite may fall back to `5174`.

## 3. Required Env Files

Root backend env:

```text
.env
```

Frontend env:

```text
apps/web/.env
```

Do not commit real `.env` files. Only `.env.example` files should be committed.

## 4. Vector Backend

For local fallback:

```env
VECTOR_BACKEND=chroma
```

For Supabase:

```env
VECTOR_BACKEND=supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_PASSWORD=
SUPABASE_VECTOR_TABLE=document_chunks
```

Before using Supabase, run:

```text
supabase/migrations/001_create_document_chunks.sql
```

in the Supabase SQL Editor, then run:

```bash
cd "/Users/vinay.paravastu/Downloads/personal projects/Final graduation project"
apps/api/.venv/bin/python scripts/refresh_vector_store.py
```

## 5. Advisor Slot Rules

Advisor slots are generated from env settings instead of a hard-coded list:

```env
ADVISOR_BUSINESS_DAYS=Monday,Tuesday,Wednesday,Thursday,Friday
ADVISOR_BUSINESS_START_HOUR=9
ADVISOR_BUSINESS_END_HOUR=18
ADVISOR_SLOT_INTERVAL_MINUTES=30
ADVISOR_SLOT_HORIZON_DAYS=14
ADVISOR_TIMEZONE=Asia/Kolkata
```

The Voice Scheduler generates date-aware slots across the configured horizon. It understands weekday names, exact month/day requests, and relative phrases such as `tomorrow`, `day after tomorrow`, `in 3 days`, and `next 3 days`.

## 6. Quick Demo Checks

FAQ retrieval:

```text
http://127.0.0.1:8000/faq/retrieve-test?query=What%20is%20the%20exit%20load%20for%20HDFC%20ELSS%20Tax%20Saver
```

App flow:

1. Open frontend.
2. Use Customer FAQ.
3. Generate Weekly Pulse.
4. Start a Vapi call in Voice Scheduler.
5. Check Approval Centre for pending MCP actions.

During slower scheduler turns, the voice UI may briefly say:

```text
Let me check that.
```

This is a frontend latency filler and not independent scheduler logic.

Vapi-specific browser testing notes are in:

```text
docs/vapi_testing.md
```
