# Architecture

## Overview

The Mutual Fund Advisor Intelligence Suite is a voice-first GenAI application that combines:

1. FAQ Chatbot (Facts-Only RAG)
2. Review Intelligence
3. Voice Appointment Scheduler

These capabilities are connected through a shared orchestration layer and an approval-gated MCP workflow.

The system is designed around five evaluation areas:

* Voice UX & Intent
* MCP & System Design
* Grounding & RAG
* AI Evaluations
* Automation, Code & Deploy

---

# System Architecture

```text
User
 │
 ▼
Dashboard UI
 │
 ├──────────── FAQ View
 │
 ├──────────── Weekly Pulse View
 │
 ├──────────── Voice Scheduler View
 │
 └──────────── Approval Centre
                  │
                  ▼
            MCP Orchestrator
                  │
 ┌────────────────┼────────────────┐
 │                │                │
 ▼                ▼                ▼
Notes Tool   Calendar Tool   Email Draft Tool
```

---

# Component Architecture

## 1. FAQ Chatbot (Grounding & RAG)

Purpose:

Provide factual mutual fund information using verified public sources.

Supported Topics:

* Exit Load
* Expense Ratio
* Benchmark
* Lock-in Period
* Riskometer
* SIP Minimum Amount
* Capital Gains Statement Guidance

Data Sources:

* AMC Factsheets
* KIM Documents
* SID Documents
* AMFI Resources
* SEBI Resources
* Kuvera Help Pages

Vector storage decision:

```text
Development fallback: local sentence-transformer embeddings + local ChromaDB
Deployment: local sentence-transformer embeddings + Supabase pgvector
```

The retrieval layer keeps embedding and vector-store access isolated so ChromaDB can be used locally and Supabase pgvector can be used in deployment without changing the FAQ route or UI.

The local embedding service loads `sentence-transformers/all-MiniLM-L6-v2`. Normal runs use cached model files; first-time setup can allow download by setting `EMBEDDING_LOCAL_FILES_ONLY=false`.

FAQ answer generation uses Groq `llama-3.3-70b-versatile` when `GROQ_API_KEY` is configured. If Groq is unavailable, the backend uses a context-only extractive fallback so the FAQ endpoint remains grounded in retrieved chunks.

### Vector Store Migration

Local ChromaDB was used for development. Supabase Postgres with pgvector is now the deployment vector backend. The RAG service still calls the same retrieval interface; only the storage adapter changes through `VECTOR_BACKEND`.

```text
VECTOR_BACKEND=supabase -> Supabase pgvector document_chunks table
VECTOR_BACKEND=chroma   -> local ChromaDB fallback under data/vector_store
```

Both backends use `sentence-transformers/all-MiniLM-L6-v2`, which produces 384-dimensional embeddings. Supabase stores those embeddings in `document_chunks.embedding vector(384)` and exposes retrieval through the `match_document_chunks` RPC.

Pipeline:

```text
User Question
      │
      ▼
Query Classifier
      │
      ▼
Retriever
      │
      ▼
Relevant Chunks
      │
      ▼
LLM Answer Generator
      │
      ▼
Citation Formatter
      │
      ▼
Response
```

Rules:

* Citation required
* Maximum 3 sentences
* No performance claims
* No investment advice
* No hallucinated facts

---

## 2. Review Intelligence

Purpose:

Convert customer reviews into actionable product insights.

Input:

```text
reviews.csv
```

Fields:

```text
review_id
date
rating
channel
review_text
```

Pipeline:

```text
Reviews CSV
      │
      ▼
Review Cleaner
      │
      ▼
Theme Detection
      │
      ▼
Quote Extraction
      │
      ▼
Weekly Product Pulse
      │
      ▼
Fee Explainer
```

Outputs:

### Weekly Product Pulse

Contains:

* Top themes
* User quotes
* Key observation
* Exactly 3 action ideas

Maximum:

```text
250 words
```

### Fee Explainer

Contains:

* Exactly 6 bullets
* Plain-language explanation
* 2 official sources
* Last checked timestamp



## 3. Voice Scheduler

Purpose:

Allow users to schedule advisor calls through voice.

Supported Intents:

* Book appointment
* Reschedule appointment
* Call preparation guidance

Pipeline:

```text
User speech
      │
      ▼
Vapi Web SDK
      │
      ├── Vapi STT
      │
      ▼
POST /scheduler/voice-turn
      │
      ▼
Intent Detection
      │
      ▼
Slot Selection
      │
      ▼
Booking Code Generation
      │
      ▼
Pending MCP Actions
      │
      ▼
Scheduler Reply
      │
      ▼
Vapi TTS
```

Example:

```text
User:
I want to book a call about my SIP mandate.

Assistant:
Many users are asking about exit load confusion this week.
I can help book a slot for your SIP mandate question.
```

The greeting dynamically uses the current Weekly Pulse top theme.

Vapi is only the voice transport layer. The frontend listens for final user transcripts from Vapi, forwards the transcript to the existing scheduler endpoint, displays the backend response, and asks Vapi to speak that response. The scheduler endpoint remains the single place where intent detection, PII deflection, booking-code generation, and MCP pending action creation happen.

## How the Three Pillars Work Together

The three pillars are designed as a connected support workflow rather than independent features.

### Step 1: Review Intelligence Identifies User Confusion

Customer reviews are analyzed to generate:

* Weekly Product Pulse
* Top Themes
* Fee Explainer

Example:

```text
Top Theme: Exit Load Confusion
```

### Step 2: FAQ Chatbot Learns From Review Insights

The generated Fee Explainer is added back into the RAG corpus.

Flow:

```text
Reviews
    ↓
Fee Explainer Generated
    ↓
Added To Vector Store
    ↓
FAQ Retrieval Improved
```

As a result, future FAQ responses can answer common fee-related questions more effectively.

### Step 3: Voice Scheduler Uses Review Context

The current Weekly Pulse Top Theme is used in the Voice Scheduler greeting.

Example:

Welcome to the Mutual Fund Support Assistant.

One of the most common support topics this week has been exit-load related questions.

How can I help you today?
```

This provides context-aware support without changing the booking workflow.

### Step 4: Advisor Receives Context

When a booking is created:

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

The advisor email draft includes:

* Booking topic
* Weekly Pulse summary
* Current Top Theme

This helps the advisor prepare before the conversation.

### End-to-End Flow

```text
Reviews
   ↓
Review Intelligence
   ↓
Weekly Pulse + Fee Explainer
   ↓
─────────────────────────
↓                       ↓
FAQ Chatbot        Voice Scheduler
↓                       ↓
Better Answers     Context-Aware Greeting
↓                       ↓
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

This creates a feedback loop between customer questions, customer feedback, and advisor interactions.


---

# Feedback Loop Into RAG

One of the key architecture requirements is that Review Intelligence improves FAQ quality.

Process:

```text
Reviews
   │
   ▼
Fee Explainer Generated
   │
   ▼
Fee Explainer Saved
   │
   ▼
Corpus Refresh
   │
   ▼
Vector Store Updated
   │
   ▼
FAQ Can Retrieve New Content
```

This allows common customer confusion to become retrievable knowledge.

---

# Booking Code Generation

Format:

```text
KV-B391
```

Rules:

* Unique per booking
* Displayed in UI
* Read aloud
* Stored in MCP actions

---

# PII Protection

The scheduler must never store:

* PAN
* Aadhaar
* Phone numbers
* Email addresses
* Folio numbers
* Bank details

Example:

```text
User:
My PAN is XXXXX1234X

Assistant:
Please do not share personal details on this call.
Please use the secure support channel instead.
```

---

# MCP Architecture

## Design Principle

The Voice Scheduler never executes external actions directly.

Required flow:

```text
Customer
      │
      ▼
Voice Scheduler
      │
      ▼
Booking Code
      │
      ▼
MCP Orchestrator
      │
      ▼
Approval Centre (Operations Console)
      │
      ▼
Approve / Reject
      │
      ▼
Calendar Tool / Notes Tool / Email Draft Tool
```

The Approval Centre represents an advisor operations console. An operations user reviews each pending action and either approves it for execution or rejects it before any tool runs.

---

## MCP Orchestrator

Purpose:

Create and manage pending actions.

Responsibilities:

* Generate action payloads
* Track status
* Route approvals
* Log executions

Statuses:

```text
pending
approved
rejected
completed
failed
```

---

## MCP Tool 1: Notes / Doc Append

Input:

```json
{
  "booking_code": "KV-B391",
  "top_theme": "exit load confusion"
}
```

Output:

```text
Shared document updated
```

---

## MCP Tool 2: Calendar Hold Creator

Input:

```json
{
  "slot": "Friday 3 PM",
  "booking_code": "KV-B391"
}
```

Output:

```text
Tentative calendar hold created
```

Stage 1:

```text
Mock calendar slots
```

Future:

```text
Google Calendar MCP
```

---

## MCP Tool 3: Email Draft Generator

Input:

```json
{
  "booking_code": "KV-B391",
  "pulse_snippet": "Exit load confusion"
}
```

Output:

```text
Draft advisor email
```

Rules:

* Draft only
* Never auto-send

---

# Data Storage

## Vector Store

Stores:

* AMC documents
* KIM
* SID
* AMFI resources
* SEBI resources
* Fee Explainer documents

Suggested:

```text
ChromaDB
```

---

## Relational Storage

Stores:

* Reviews
* Weekly Pulse
* Booking records
* MCP actions
* Evaluation results

Suggested:

```text
SQLite (development)
Postgres (deployment)
```

---

# Evaluation Architecture

Three evaluation layers are implemented.

## Retrieval Accuracy

Checks:

* Faithfulness
* Relevance
* Citation Accuracy

---

## Compliance & Safety

Checks:

* Investment advice refusal
* PII protection
* Hallucination prevention

---

## UX & Structure

Checks:

* Weekly Pulse formatting
* Fee Explainer formatting
* Voice greeting behavior
* Booking code generation
* MCP action creation

---

# Deployment Architecture

Frontend:

```text
React + Vite
```

Backend:

```text
FastAPI
```

Suggested Deployment:

```text
Frontend → Vercel

Backend → Render
```

The application is exposed through a single dashboard entry point with all three pillars accessible from one interface.
