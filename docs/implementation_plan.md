# Implementation Plan

This document defines the phase-wise implementation plan for the Mutual Fund Advisor Intelligence Suite.

The goal is to build the project in small working increments so that every phase produces something demoable.

---

# Build Strategy

The project should be built in this order:

1. Code & Deploy Skeleton
2. Grounding & RAG
3. Review Intelligence Automation
4. Voice UX & Intent
5. MCP & Human Approval
6. AI Evaluations
7. Final Demo, Deployment & Submission

The first priority is to create a working dashboard with mock APIs. Real AI, RAG, voice, and MCP integrations should be added only after the skeleton works.

Project-level todos from Phase 2 onward are tracked in `docs/todo.md`, including the deployment migration path from local ChromaDB to Supabase pgvector and the final hosted rollout checklist.

---

# Phase 1 — Code & Deploy Skeleton

Status: complete.

## Goal

Create the basic full-stack application with a single dashboard and mock backend APIs.

## Evaluation Area

Automation, Code & Deploy

## Tasks

### Frontend

Create a React + Vite JavaScript app with four views:

1. FAQ
2. Weekly Pulse
3. Voice Scheduler
4. Approval Centre

The first version can use simple CSS. Tailwind can be added later.

### Backend

Create a FastAPI backend with mock routes:

```text
GET /
POST /faq/ask
POST /pulse/generate
POST /scheduler/voice-turn
GET /approvals/pending
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/reject
```

### Data

Create placeholder folders:

```text
data/reviews
data/sources
data/evals
data/outputs
```

### Mock Behavior

The app should show:

* FAQ answer with mock citation
* Weekly Pulse with mock top theme
* Voice Scheduler response with booking code
* Approval Centre with three pending actions

## Exit Criteria

Phase 1 is complete when:

* Frontend runs locally
* Backend runs locally
* All four dashboard views are visible
* Frontend can call backend APIs
* Approval Centre can approve/reject mock actions

## Suggested Commit

```text
phase-1-dashboard-skeleton
```

---

Current Phase 1 notes:

* React + Vite dashboard runs locally.
* FastAPI mock backend runs locally.
* FAQ, Weekly Pulse, Voice Scheduler, and Approval Centre views are visible.
* Frontend API helper calls backend routes.
* Approval Centre can approve or reject mock MCP actions.
* Sidebar-based dashboard navigation replaced the earlier top-tab layout.

---

# Phase 2 — Grounding & RAG

## Goal

Build the facts-only FAQ engine using verified public sources.

## Evaluation Area

Grounding & RAG

## Current RAG Storage Decision

Use local sentence-transformer embeddings with local ChromaDB for development:

```text
Official Sources
      ↓
Chunks
      ↓
sentence-transformers/all-MiniLM-L6-v2
      ↓
Local ChromaDB
      ↓
retrieve_relevant_chunks()
```

For final deployment, store the same `sentence-transformers/all-MiniLM-L6-v2` embeddings in hosted Supabase pgvector.

Embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Default embedding dimension:

```text
384
```

Local model loading:

```text
EMBEDDING_LOCAL_FILES_ONLY=true
```

Set `EMBEDDING_LOCAL_FILES_ONLY=false` only when the MiniLM model needs to be downloaded for the first time.

Current Phase 2 notes:

* FAQ memory supports contextual follow-ups with `session_id` and `thread_id`.
* Retrieval is abstracted behind a vector-store adapter.
* Supabase pgvector support has been implemented in parallel with Chroma fallback.
* FAQ guardrails refuse advice-oriented prompts and preserve explicit scheme switching.

## Tasks

### Source Selection

Select:

* 1 AMC
* 3–5 schemes
* 30+ official/public URLs

Sources should include:

* AMC factsheets
* KIM documents
* SID documents
* AMFI education pages
* SEBI investor pages
* Kuvera help pages

### Source Manifest

Create:

```text
data/sources/source_manifest.csv
```

Required columns:

```text
source_id
url
title
source_type
scheme_name
topic
date_checked
is_official
```

### Ingestion

Build scripts:

```text
scripts/ingest_sources.py
scripts/refresh_vector_store.py
```

Pipeline:

```text
Source Manifest
      ↓
Fetch / Load Documents
      ↓
Clean Text
      ↓
Chunk Text
      ↓
Generate Embeddings
      ↓
Store in Vector DB
```

### FAQ RAG

Replace mock FAQ response with RAG:

```text
Question
   ↓
Classification
   ↓
Retrieval
   ↓
Answer Generation
   ↓
Citation Formatting
```

Phase 2B implementation:

```text
Question
   ↓
Compliance Guardrails
   ↓
Retrieve Top 5 Chunks
   ↓
Build Context From Retrieved Chunks
   ↓
Groq llama-3.3-70b-versatile
   ↓
3-Sentence Grounded Answer
   ↓
Citation Formatting
```

Advice, recommendation, return prediction, and portfolio allocation requests are refused and redirected to AMFI investor education.

If `GROQ_API_KEY` is not configured or the Groq API is unavailable, the FAQ endpoint falls back to a context-only extractive answer. The fallback still uses retrieved chunks only and does not generate unsupported facts.

### Guardrails

Implement rules:

* Refuse investment advice
* Refuse performance predictions
* Do not collect PII
* Ask clarification only when scheme is ambiguous
* Say data is missing when the corpus does not contain the answer

## Exit Criteria

Phase 2 is complete when:

* Source manifest has 30+ URLs
* Documents are ingested
* Vector search returns source-backed chunks
* FAQ answer includes citation
* Advice prompts are refused
* Missing data is handled explicitly

## Suggested Commit

```text
phase-2-rag-faq
```

---

# Phase 3 — Review Intelligence Automation

## Goal

Process user reviews into a Weekly Product Pulse and Fee Explainer.

## Evaluation Areas

* Automation, Code & Deploy
* Grounding & RAG

## Tasks

### Reviews Dataset

Create:

```text
data/reviews/sample_reviews.csv
```

Required columns:

```text
review_id
date
channel
rating
review_text
```

Dataset rules:

* 30–50 rows
* Last 8–12 weeks
* No PII
* Include realistic mutual fund support issues

Example themes:

* Exit load confusion
* SIP mandate failure
* Capital gains statement confusion
* Expense ratio confusion
* Redemption status delay
* App navigation issues

### Review Processing

Build:

```text
scripts/ingest_reviews.py
```

Pipeline:

```text
Reviews CSV
    ↓
Clean Reviews
    ↓
Detect Themes
    ↓
Extract Quotes
    ↓
Generate Weekly Pulse
    ↓
Generate Fee Explainer
```

### Weekly Product Pulse

Must include:

* Top themes
* At least 1 user quote
* Key observation
* Exactly 3 action ideas
* Maximum 250 words

### Fee Explainer

Must include:

* Exactly 6 bullets
* 2 official source links
* Last checked date
* Plain-language explanation

### RAG Feedback Loop

After Fee Explainer generation:

```text
Fee Explainer
    ↓
Save as document
    ↓
Add to source manifest
    ↓
Refresh vector store
    ↓
FAQ can retrieve it
```

## Exit Criteria

Phase 3 is complete when:

* Review CSV exists
* Weekly Pulse is generated
* Fee Explainer is generated
* Fee Explainer is added to RAG corpus
* FAQ can answer a fee-confusion question using the generated explainer

## Suggested Commit

```text
phase-3-review-intelligence
```

---

# Phase 4 — Voice UX & Intent

## Goal

Build the voice-first advisor appointment scheduler.

## Evaluation Area

Voice UX & Intent

## Tasks

### Voice Input

Implement one of the following:

Stage 1:

```text
Typed transcript box
```

Stage 2:

```text
Browser speech-to-text
```

### Voice Scheduler UI

The Scheduler View should show:

* Microphone button
* Live transcript
* Assistant response
* Available mock slot
* Booking confirmation
* Booking code

### Intent Detection

Support:

* Book appointment
* Reschedule appointment
* Ask what to prepare
* PII deflection

### Dynamic Greeting

The greeting must include the current Weekly Pulse top theme.

Example:

```text
Many users are asking about exit load confusion this week. I can help book a slot for that.
```

### Booking Code

Generate codes in this format:

```text
KV-B391
```

Rules:

* Unique per booking
* Displayed in UI
* Spoken back to user
* Passed to MCP Orchestrator

## Exit Criteria

Phase 4 is complete when:

* User can enter or speak a booking request
* System detects booking intent
* System confirms a mock slot
* Booking code is generated
* Top theme appears in greeting
* PII is deflected

## Suggested Commit

```text
phase-4-voice-scheduler
```

---

# Phase 5 — MCP & Human Approval

## Goal

Build the approval-gated MCP orchestration layer.

## Evaluation Area

MCP & System Design

## Design Rule

The Voice Scheduler must never directly execute tools.

Correct flow:

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
Calendar Tool
Notes Tool
Email Draft Tool
```

After a booking is created, the system generates three pending MCP actions. These actions appear in the Approval Centre, which represents an advisor operations console. An operations user reviews and approves the actions before the underlying tools execute.

## Required MCP Tools

### 1. Notes / Doc Append Tool

Inputs:

```text
date
top_theme
weekly_pulse
fee_explainer
booking_code
```

Output:

```text
Appended notes entry
```

### 2. Calendar Hold Creator

Inputs:

```text
topic
slot
booking_code
```

Output:

```text
Tentative calendar hold
```

Stage 1 can use a mock calendar.

### 3. Email Draft Generator

Inputs:

```text
advisor_details
pulse_snippet
booking_code
```

Output:

```text
Draft advisor email
```

Email must never auto-send.

## Approval Centre

The Approval Centre represents the advisor operations console.

The UI must show:

* Pending action type
* Input payload summary
* Booking code
* Approve button
* Reject button
* Status

Statuses:

```text
pending
approved
rejected
completed
failed
```

## Exit Criteria

Phase 5 is complete when:

* Booking creates three pending MCP actions
* Approval Centre displays them
* Approving an action executes the mock MCP tool
* Rejecting an action prevents execution
* All actions are logged

## Suggested Commit

```text
phase-5-mcp-approval
```

---

# Phase 6 — AI Evaluations

## Goal

Implement runnable checks that prove the system works safely and reliably.

## Evaluation Area

AI Evaluations

## Eval 1 — Retrieval Accuracy

Create:

```text
data/evals/golden_questions.json
```

Minimum:

```text
5 questions
```

Question types:

* Scheme fact
* Exit load
* Minimum SIP
* Fee confusion
* Platform guidance

Metrics:

```text
retrieval_success = pass/fail
citation_presence = pass/fail
relevance = pass/fail
```

## Eval 2 — Compliance & Safety

Create:

```text
data/evals/adversarial_prompts.json
```

Minimum:

```text
5 prompts
```

Prompt types:

* Investment advice request
* PII sharing attempt
* Unsupported performance claim
* Out-of-scope request
* Hallucination trap

Metric:

```text
5/5 pass target
```

## Eval 3 — UX & Structure

Create:

```text
data/evals/ux_eval_cases.json
```

Checks:

* Weekly Pulse <= 250 words
* Weekly Pulse has exactly 3 action ideas
* Weekly Pulse has at least 1 quote
* Fee Explainer has exactly 6 bullets
* Fee Explainer has 2 official source links
* Fee Explainer has Last checked date
* Voice greeting includes top theme
* Booking code is generated
* Calendar Hold action exists
* Notes Entry action exists
* Email Draft action exists

## Script

Create:

```text
scripts/run_evals.py
```

The script should output:

```text
RAG Eval: PASS
Safety Eval: PASS
UX Eval: PASS
```

## Exit Criteria

Phase 6 is complete when:

* Eval files exist
* Eval script runs locally
* Results are saved to data/outputs
* At least one eval can be shown live in demo

## Suggested Commit

```text
phase-6-evals
```

---

# Phase 7 — Final Demo & Submission

## Goal

Prepare the deployed prototype and final submission package.

## Evaluation Areas

All five areas:

* Voice UX & Intent
* MCP & System Design
* Grounding & RAG
* AI Evaluations
* Automation, Code & Deploy

## Final Tasks

### Deployment

Deploy:

```text
Frontend → Vercel
Backend → Render
```

or any equivalent platform.

### Documentation

Finalize:

```text
README.md
docs/architecture.md
docs/implementation_plan.md
docs/mcp_workflow.md
docs/evaluation_strategy.md
docs/demo_script.md
```

### Demo Video

The 5-minute demo should show:

1. Dashboard with all pillars
2. Review CSV processed into Weekly Pulse
3. Fee Explainer generated
4. Fee Explainer added back into RAG
5. FAQ answering with citation
6. Voice Scheduler using top theme in greeting
7. Booking code generated
8. Approval Centre showing three MCP actions
9. Approving the actions
10. At least one eval running live

## Exit Criteria

Phase 7 is complete when:

* Public app link is available
* GitHub repo is complete
* Demo video is recorded
* Eval outputs are included
* Source manifest has 30+ URLs
* Reviews CSV has 30–50 entries

## Suggested Commit

```text
phase-7-final-submission
```

---

# Recommended First Coding Session

Start only with Phase 1.

Do not build RAG, MCP, or voice yet.

The first target is:

```text
A dashboard with four working views and mock API calls.
```

Once that works, proceed to RAG.
