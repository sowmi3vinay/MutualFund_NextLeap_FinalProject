# Mutual Fund Advisor Intelligence Suite

Voice-first mutual fund support system with three connected pillars:

1. Facts-only FAQ assistant with citations
2. Weekly Product Pulse from review data
3. Voice-based advisor scheduler with approval-gated operations

The project is local-demo ready and deployment-prepared. Core business logic lives in the FastAPI backend, while the React + Vite frontend provides four operational surfaces through a left sidebar:

- Customer: Facts-only AI assistant
- Product: Weekly Pulse
- Advisor: Voice Scheduler
- Operations: Approval Centre

## Current Status

Implemented:

- FAQ RAG with grounded answers and citation links
- FAQ memory for contextual follow-ups
- Review Intelligence from review CSV
- Fee Explainer feedback loop into the RAG corpus
- Vapi-based voice scheduler transport
- Date-aware slot selection and booking-code generation
- Sample advisor roster with conflict checks
- Approval-gated MCP workflow
- Google Sheets logging after approval
- Eval framework for RAG, safety, and UX

Pending before final hosted rollout:

- Deploy frontend
- Deploy backend
- Configure production Supabase project and ingest vectors
- Add final public app URL
- Record final demo / submission assets

## Non-Negotiable Architecture Rule

The Voice Scheduler must never execute tools directly.

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
Approval Centre (Operations Console)
   ↓
Approve / Reject
   ↓
Calendar Tool / Notes Tool / Email Draft Tool
```

The scheduler may detect intent, select a slot, assign an advisor, generate a booking code, and create pending actions. Tool execution happens only after human approval.

## Stack

### Frontend

- React + Vite
- CSS-based dashboard UI
- Vapi Web SDK for browser STT/TTS transport

### Backend

- FastAPI
- Groq `llama-3.3-70b-versatile` for grounded answer generation when configured
- Extractive fallback when Groq is unavailable

### Retrieval

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Production vector backend: Supabase pgvector
- Local fallback vector backend: ChromaDB

### Ops / Logging

- Local booking persistence: `data/outputs/advisor_bookings.json`
- Google Sheets logging after approval
- Mock MCP tools for calendar hold, notes entry, and email draft

## Pillars

### 1. Customer FAQ

Current behavior:

- answers only from retrieved corpus context
- includes citations
- refuses investment advice, recommendations, and return predictions
- supports thread memory for follow-ups like:
  - `What about its benchmark?`
  - `What about its riskometer?`

Important files:

- `apps/api/routes/faq.py`
- `apps/api/services/rag_service.py`
- `apps/api/services/faq_memory.py`
- `apps/api/services/compliance_guardrails.py`

### 2. Product Pulse

Current behavior:

- reads review CSV data
- generates weekly product pulse
- generates fee explainer
- writes outputs to:
  - `data/outputs/weekly_pulse.json`
  - `data/outputs/fee_explainer.md`
- supports optional vector-refresh feedback loop

UI note:

- the dashboard pulse action skips full vector refresh by default so the UI stays responsive

Important files:

- `apps/api/routes/pulse.py`
- `apps/api/services/review_intelligence.py`

### 3. Advisor Voice Scheduler

Current behavior:

- Vapi captures speech
- final transcript is sent to `POST /scheduler/voice-turn`
- backend performs intent detection, scheduling, booking-code generation, advisor assignment, and MCP action creation
- backend reply is spoken back through Vapi TTS

Important details:

- Scheduler is date-aware:
  - `today`
  - `tomorrow`
  - `day after tomorrow`
  - `in 3 days`
  - weekday names
  - explicit dates
- Slots are generated from business-hour configuration, not hard-coded lists
- Sample advisors:
  - Asha Mehta
  - Rohan Iyer
  - Neha Kapoor
- same advisor cannot be double-booked for the same slot
- a short latency-based filler line, `Let me check that.`, is used only when backend response takes a moment

Important files:

- `apps/api/routes/scheduler.py`
- `apps/api/services/voice_scheduler.py`
- `apps/api/services/advisor_scheduler.py`
- `apps/web/src/views/SchedulerView.jsx`

### 4. Operations Approval Centre

Current behavior:

- shows pending MCP actions
- allows approve / reject
- displays booking code, assigned advisor, slot, transcript summary, and status
- notes tool can append approved booking rows to Google Sheets

Important files:

- `apps/api/routes/approvals.py`
- `apps/api/services/mcp_orchestrator.py`
- `apps/web/src/views/ApprovalCentre.jsx`

## Local Run

Backend:

```bash
cd apps/api
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd apps/web
source ~/.nvm/nvm.sh
npm run dev -- --host 127.0.0.1
```

Typical local URLs:

- Frontend: `http://127.0.0.1:5173/`
- Backend: `http://127.0.0.1:8000`

More restart detail is in `docs/local_runbook.md`.

## Environment Summary

Backend / root `.env`:

```text
GROQ_API_KEY=
APP_ENV=
VECTOR_BACKEND=supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_PASSWORD=
SUPABASE_VECTOR_TABLE=document_chunks
GOOGLE_SERVICE_ACCOUNT_JSON=
GOOGLE_SHEETS_BOOKING_SPREADSHEET_ID=
GOOGLE_SHEETS_BOOKING_WORKSHEET=Bookings
```

Frontend `apps/web/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_VAPI_PUBLIC_KEY=
VITE_VAPI_ASSISTANT_ID=
```

For deployment, prefer `GOOGLE_SERVICE_ACCOUNT_JSON` instead of a local credential file path.

## Deployment Direction

Recommended deployment split:

- Frontend: Vercel / Netlify / Render static site
- Backend: Render / Railway / Fly.io / Python web service
- Vector store: Supabase pgvector

Deployment prep already in place:

- backend hosted startup config
- backend CORS env support
- frontend API base URL env support
- Supabase migration SQL
- swappable vector-store adapter

Use `docs/deployment.md` as the deployment checklist.

## Current Known Gaps

- Not all HDFC schemes are present in the current corpus
- Google Calendar is not yet a full live calendar sync
- Email remains draft-only
- Advisor availability is still sample-roster based, not live enterprise occupancy

## Key Files

- `apps/api/routes/faq.py`
- `apps/api/routes/pulse.py`
- `apps/api/routes/scheduler.py`
- `apps/api/routes/approvals.py`
- `apps/api/services/rag_service.py`
- `apps/api/services/review_intelligence.py`
- `apps/api/services/voice_scheduler.py`
- `apps/api/services/mcp_orchestrator.py`
- `apps/api/services/advisor_scheduler.py`
- `apps/web/src/App.jsx`
- `apps/web/src/views/FAQView.jsx`
- `apps/web/src/views/PulseView.jsx`
- `apps/web/src/views/SchedulerView.jsx`
- `apps/web/src/views/ApprovalCentre.jsx`

## Final Pre-Deployment Checklist

- Set production env vars
- Run Supabase migration
- Ingest source chunks into Supabase
- Verify FAQ answers against production backend
- Verify Vapi frontend env vars
- Verify Google Sheets credentials
- Set frontend production URL in backend `CORS_ORIGINS`
- Publish frontend and backend

Once those are done, the project should be ready for hosted demo submission.
