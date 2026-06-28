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

The Voice Scheduler now generates date-aware tentative slots from business-hour configuration, assigns an available sample advisor, and creates booking records locally. After approval, the tools execute according to their current demo behavior:

- Calendar Hold: mock hold / calendar-link style output
- Notes Entry: append operational booking details, including Google Sheets logging when configured
- Email Draft: advisor draft only, never auto-send

A later version can replace the calendar-link behavior with full Google Calendar API event creation while keeping the same approval-gated architecture.

Implementation contract:

- `voice_scheduler.py` may create or update booking records.
- `voice_scheduler.py` may assign an available advisor for the selected slot.
- `voice_scheduler.py` may request pending actions from the MCP Orchestrator.
- `voice_scheduler.py` must not call `calendar_hold_tool.py`, `doc_append_tool.py`, or `email_draft_tool.py` directly.
- MCP tool execution is only allowed from the approval path after a human approves an action.
- Rejected actions must be stored as rejected and must not execute.
