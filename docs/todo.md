# Project Todo List

This list tracks work from Phase 2 onward. Prioritize current-phase tasks first, then revisit deployment items near Phase 7.

## Current Priority — Phase 2 Grounding & RAG

- [x] Create `data/sources/source_manifest.csv` with 30+ official/public URLs.
- [x] Use HDFC as the first AMC scope.
- [x] Include 3–5 HDFC schemes plus general HDFC, AMFI, SEBI, and Kuvera support sources.
- [x] Implement source ingestion in `scripts/ingest_sources.py`.
- [x] Extract text from HTML pages.
- [x] Extract text from PDF documents.
- [x] Chunk source text into overlapping chunks.
- [x] Use local sentence-transformer embeddings for source chunks.
- [x] Store chunks and metadata in local ChromaDB for development.
- [x] Persist local ChromaDB under `data/vector_store/`.
- [x] Implement `retrieve_relevant_chunks(query, top_k=5)` in `apps/api/services/rag_service.py`.
- [x] Add `GET /faq/retrieve-test?query=...` for retrieval testing.
- [x] Replace `/faq/ask` mock answer behavior with grounded RAG answer generation.
- [x] Add Groq-powered answer generation for FAQ.
- [x] Limit FAQ answers to 3 sentences.
- [x] Include source citation URLs in FAQ responses.
- [x] Refuse investment advice, fund recommendations, return predictions, and portfolio allocation advice.
- [x] Return corpus-insufficient response when retrieval confidence is low.

## RAG Architecture Decision

- [x] Use local sentence-transformer embeddings for the current RAG implementation.
- [x] Use local ChromaDB as the development vector store.
- [x] Keep vector-store access isolated so deployment can switch storage later.
- [x] Document embedding model name and vector dimensions once selected.
- [x] Document first-time local embedding model download behavior.

## Later Deployment Todo — Supabase pgvector

- [ ] Create a Supabase project for deployed vector storage.
- [x] Keep deployed embedding provider as sentence-transformers/all-MiniLM-L6-v2.
- [ ] Enable the `vector` extension in Supabase Postgres.
- [x] Design a `document_chunks` table with text, embedding, and source metadata.
- [x] Add environment variables for Supabase URL and service key.
- [x] Create a vector-store adapter interface for ChromaDB vs Supabase.
- [x] Implement Supabase pgvector insert/upsert for chunks.
- [x] Implement Supabase similarity search for retrieval.
- [x] Add migration notes from local ChromaDB to Supabase pgvector.
- [x] Update deployment README with Supabase setup steps.
- [ ] Confirm deployed backend does not depend on local filesystem vector storage.

## Phase 3 Review Intelligence

- [x] Expand `data/reviews/sample_reviews.csv` to 30–50 rows.
- [x] Implement review ingestion and cleaning.
- [x] Generate Weekly Product Pulse.
- [x] Generate Fee Explainer.
- [x] Add generated Fee Explainer back into the RAG corpus.
- [x] Refresh vector store after Fee Explainer generation.

## Phase 4 Voice UX & Intent

- [x] Add microphone input or typed transcript fallback.
- [x] Implement intent detection.
- [x] Generate unique booking codes.
- [x] Add PII deflection.
- [x] Make the greeting use the current Weekly Pulse top theme.

## Phase 5 MCP & Human Approval

- [x] Add MCP Orchestrator service.
- [x] Create pending Calendar Hold actions after booking.
- [x] Create pending Notes / Doc Append actions after booking.
- [x] Create pending Email Draft actions after booking.
- [x] Execute mock tools only after approval.
- [x] Log approved and rejected actions.

## Phase 6 AI Evaluations

- [x] Add retrieval accuracy eval.
- [x] Add compliance and safety eval.
- [x] Add tone and structure eval.
- [x] Save eval results to `data/outputs/eval_results.json`.

## Phase 7 Final Demo & Submission

- [ ] Deploy frontend.
- [ ] Deploy backend.
- [x] Add deployment configuration for backend CORS, Render-style FastAPI startup, and Vite API URL.
- [x] Document current deploy path using bundled ChromaDB vector storage.
- [x] Add Supabase pgvector migration and vector-store backend selector.
- [ ] Configure deployed Supabase project and ingest deployed vector storage.
- [ ] Add public app URL.
- [x] Prepare sample Q&A pairs.
- [x] Prepare sample voice transcript.
- [ ] Record 5-minute demo video.
- [x] Document known limitations.
