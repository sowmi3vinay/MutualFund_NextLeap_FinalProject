# Limitations

- The application is feature-complete for a local capstone demo, but hosted production deployment is still pending.
- The source corpus is intentionally scoped to one AMC and a limited set of HDFC schemes, so some scheme-specific questions still return corpus-insufficient responses.
- Supabase pgvector is the intended production vector backend, but it still needs final validation in the hosted deployment after production ingest.
- Review data is sample/simulated support feedback and should not be treated as production customer data.
- Advisor allocation currently uses a sample roster and local conflict detection, not live enterprise calendar occupancy.
- MCP tools are still demo-focused implementations. They validate approval-gated orchestration, but they are not yet full production integrations.
- Calendar handling is not yet a full Google Calendar sync with live attendee management.
- Email actions create drafts only and never auto-send.
- Google Sheets logging is available after approval, but it is an operational log, not a replacement for a production CRM or booking system.
- Vapi is used only as the browser voice transport layer. Voice quality, latency, and interruption behavior still depend partly on Vapi and the chosen transcriber/voice configuration.
- The scheduler uses a short filler line when backend latency is noticeable. This improves responsiveness, but it is still a frontend UX patch rather than true low-latency streaming orchestration.
- The assistant refuses investment advice, return predictions, fund recommendations, and portfolio allocation guidance by design.
- PII should not be shared in the voice flow; detected personal details are deflected to secure support channels.
