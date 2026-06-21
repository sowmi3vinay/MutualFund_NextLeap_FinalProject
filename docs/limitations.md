# Limitations

- The application is complete through Phase 6 for local demonstration, but it is not deployed yet.
- The source corpus is intentionally scoped to one AMC and a small set of HDFC schemes.
- Local RAG can use ChromaDB as a fallback; deployment uses the Supabase pgvector adapter after the Supabase project is configured and ingested.
- Review data is sample/simulated support feedback and should not be treated as production customer data.
- Calendar slots are mocked in the first version.
- MCP tools are mock implementations; they prove approval-gated orchestration but do not call real calendar, notes, or email systems.
- Email actions create drafts only and never auto-send.
- Browser voice input uses the Web Speech API, so support depends on the user's browser.
- The assistant refuses investment advice, return predictions, fund recommendations, and portfolio allocation guidance.
- PII should not be shared in the voice flow; detected personal details are deflected to secure support channels.
