# Architecture

## Overview

The Mutual Fund Advisor Intelligence Suite is a multi-surface support system built around four visible dashboard surfaces and one shared backend architecture:

- Customer FAQ
- Weekly Product Pulse
- Advisor Voice Scheduler
- Operations Approval Centre

The architecture is intentionally human-in-the-loop. The scheduler can prepare actions, but external tool execution remains gated by approval.

## Current System View

```text
User
 │
 ▼
React + Vite Dashboard
 │
 ├──────── FAQ View
 ├──────── Weekly Pulse View
 ├──────── Voice Scheduler View
 └──────── Approval Centre
          │
          ▼
     FastAPI Backend
          │
 ┌────────┼───────────────┬─────────────────────┐
 │        │               │                     │
 ▼        ▼               ▼                     ▼
FAQ     Review      Voice Scheduler      MCP Orchestrator
RAG     Intelligence    Logic                  │
 │        │               │                    │
 ▼        ▼               ▼                    ▼
Vector   Pulse +      Booking Store      Approval Actions
Store    Fee Output   + Advisor Logic          │
                                              ▼
                                 Calendar / Notes / Email Tools
```

## Frontend Architecture

Frontend lives in `apps/web`.

Current UI structure:

- left sidebar navigation
- four operational surfaces instead of top tabs
- local browser thread persistence for FAQ
- Vapi-powered voice interaction in Scheduler view

Primary frontend files:

- `apps/web/src/App.jsx`
- `apps/web/src/views/FAQView.jsx`
- `apps/web/src/views/PulseView.jsx`
- `apps/web/src/views/SchedulerView.jsx`
- `apps/web/src/views/ApprovalCentre.jsx`

## Backend Architecture

Backend lives in `apps/api`.

Key routes:

```text
POST /faq/ask
GET  /faq/retrieve-test
POST /pulse/generate
GET  /scheduler/greeting
POST /scheduler/voice-turn
GET  /approvals/pending
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/reject
```

Core backend services:

- `rag_service.py`
- `faq_memory.py`
- `review_intelligence.py`
- `voice_scheduler.py`
- `advisor_scheduler.py`
- `mcp_orchestrator.py`
- `eval_runner.py`

## FAQ Architecture

Purpose:

- provide facts-only mutual fund answers grounded in retrieved source chunks

Pipeline:

```text
Question
   ↓
Compliance / advice guardrails
   ↓
FAQ memory contextualization
   ↓
Embedding generation
   ↓
Vector retrieval + keyword hybrid retrieval
   ↓
Grounded answer generation
   ↓
Citation formatting
```

Current implementation details:

- follow-up memory keyed by `session_id` and `thread_id`
- explicit scheme detection prevents memory from overwriting new scheme questions
- advice requests are refused and redirected to AMFI education
- answer generation uses Groq when available and extractive fallback otherwise

Relevant files:

- `apps/api/routes/faq.py`
- `apps/api/services/faq_memory.py`
- `apps/api/services/rag_service.py`
- `apps/api/services/llm_service.py`
- `apps/api/services/compliance_guardrails.py`

## Vector Store Architecture

Embeddings:

- `sentence-transformers/all-MiniLM-L6-v2`
- 384 dimensions

Backend selection:

```text
VECTOR_BACKEND=supabase -> deployment backend
VECTOR_BACKEND=chroma   -> local fallback backend
```

Current design goal:

- retrieval interface remains stable
- storage backend can swap without changing FAQ API or frontend

Supabase path:

- `document_chunks` table
- `match_document_chunks` RPC
- `supabase/migrations/001_create_document_chunks.sql`

Local fallback path:

- ChromaDB under `data/vector_store/`

## Review Intelligence Architecture

Purpose:

- convert support review CSV data into actionable product insights
- feed fee confusion back into the FAQ corpus

Pipeline:

```text
Reviews CSV
   ↓
Cleaning + theme detection
   ↓
Weekly Product Pulse
   ↓
Fee Explainer
   ↓
Output files
   ↓
Optional vector refresh feedback loop
```

Outputs:

- `data/outputs/weekly_pulse.json`
- `data/outputs/fee_explainer.md`

Important current behavior:

- UI pulse generation does not force a full vector refresh by default
- backend still supports refresh when explicitly requested

Relevant files:

- `apps/api/routes/pulse.py`
- `apps/api/services/review_intelligence.py`

## Voice Scheduler Architecture

Purpose:

- handle advisor booking flow through voice without bypassing backend logic

Current voice transport flow:

```text
User speech
   ↓
Vapi Web SDK
   ↓
Final transcript in browser
   ↓
POST /scheduler/voice-turn
   ↓
Intent detection + slot selection + booking code generation
   ↓
Pending MCP actions
   ↓
Backend reply
   ↓
Vapi TTS
```

Important rule:

- Vapi is transport-only
- Vapi must not reason about scheduling itself
- Vapi must not generate bookings, times, or actions

Current scheduler behavior:

- detects booking / reschedule / preparation intents
- deflects PII
- supports date-aware scheduling:
  - weekdays
  - explicit dates
  - `today`
  - `tomorrow`
  - `day after tomorrow`
  - `in 3 days`
  - `next 3 days`
- assigns sample advisor from roster
- blocks same-advisor same-slot conflicts
- generates booking codes
- creates pending MCP actions only

Current advisor allocation layer:

- Asha Mehta
- Rohan Iyer
- Neha Kapoor

Persistence:

- local booking store: `data/outputs/advisor_bookings.json`

Frontend voice UX note:

- a latency-based filler line, `Let me check that.`, may be spoken if backend response is delayed
- filler is frontend-controlled, not Vapi-authored

Relevant files:

- `apps/api/services/voice_scheduler.py`
- `apps/api/services/advisor_scheduler.py`
- `apps/web/src/views/SchedulerView.jsx`

## Approval-Gated MCP Architecture

Required flow:

```text
Customer
   ↓
Voice Scheduler
   ↓
Booking Code
   ↓
MCP Orchestrator
   ↓
Approval Centre
   ↓
Approve / Reject
   ↓
Calendar Tool / Notes Tool / Email Draft Tool
```

Current MCP design:

- scheduler creates pending actions
- approval centre surfaces those actions
- approved actions execute mock tools
- rejected actions remain rejected and do not run

Tool behavior today:

- Calendar Hold: mock hold / calendar-link style behavior
- Notes Entry: can append approved booking records to Google Sheets
- Email Draft: draft-only, never auto-send

Relevant files:

- `apps/api/routes/approvals.py`
- `apps/api/services/mcp_orchestrator.py`
- `apps/api/mcp_tools/calendar_hold_tool.py`
- `apps/api/mcp_tools/doc_append_tool.py`
- `apps/api/mcp_tools/email_draft_tool.py`

## Google Sheets Logging

Current behavior:

- booking details can be appended to a Google Sheet after approval
- intended for operations visibility and demo persistence

Preferred deployment credential mode:

- `GOOGLE_SERVICE_ACCOUNT_JSON`

Local fallback:

- `GOOGLE_SERVICE_ACCOUNT_FILE`

Current sheet usage is approval-time logging, not scheduler-direct logging, which preserves architecture boundaries.

## Deployment Architecture

Recommended hosted split:

- Frontend: Vercel / Netlify / static hosting
- Backend: Render / Railway / Fly.io / Python web host
- Vector store: Supabase pgvector

Production env responsibilities:

- frontend:
  - `VITE_API_BASE_URL`
  - `VITE_VAPI_PUBLIC_KEY`
  - `VITE_VAPI_ASSISTANT_ID`
- backend:
  - `GROQ_API_KEY`
  - `VECTOR_BACKEND=supabase`
  - `SUPABASE_*`
  - `GOOGLE_*`
  - `CORS_ORIGINS`

## Current Readiness Summary

Implemented:

- FAQ
- review intelligence
- Vapi scheduler
- advisor assignment
- approval centre
- Google Sheets logging
- Supabase vector adapter
- eval framework

Pending before final hosted submission:

- production deployment
- Supabase production ingest validation
- final public URL
- final demo recording
