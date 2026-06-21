# Approval-Gated MCP Workflow

The Voice Scheduler must not directly create calendar events, write notes, or send emails.

After a booking is created, the system generates three pending MCP actions. These actions appear in the Approval Centre, which represents an advisor operations console. An operations user reviews and approves or rejects the actions before the underlying tools execute.

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
Calendar Tool
Notes Tool
Email Draft Tool
```

This keeps the system human-in-the-loop and prevents external actions from happening automatically.

Version one uses mock calendar slots to prove the voice booking flow. A later version can replace the mock calendar tool with a real calendar MCP connector, while keeping the same approval-gated architecture.

Implementation contract:

- `voice_scheduler.py` may create or update booking records.
- `voice_scheduler.py` may request pending actions from the MCP Orchestrator.
- `voice_scheduler.py` must not call `calendar_hold_tool.py`, `doc_append_tool.py`, or `email_draft_tool.py` directly.
- MCP tool execution is only allowed from the approval path after a human approves an action.
- Rejected actions must be stored as rejected and must not execute.
