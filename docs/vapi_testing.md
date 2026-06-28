# Vapi Testing Notes

The Voice Scheduler uses Vapi only as the browser voice layer.

```text
User speech
  -> Vapi STT
  -> POST /scheduler/voice-turn
  -> backend scheduler logic
  -> Vapi TTS
```

The backend remains responsible for:

- Weekly Pulse greeting
- PII deflection
- intent detection
- booking-code generation
- pending MCP action creation

## Dashboard Configuration

Use an assistant configured to stay quiet until the web app sends speech.

Recommended settings:

- First message mode: assistant waits for user
- Keep the assistant prompt minimal, for example: "Capture user speech for the scheduler. Do not create bookings yourself."
- Do not configure Vapi tools that create calendar events, notes, or emails.
- Keep partial transcripts enabled in the transcriber settings.

The frontend also passes `firstMessageMode: assistant-waits-for-user` when starting the call and speaks the scheduler greeting itself.

The frontend may also speak a short latency filler, `Let me check that.`, if the backend scheduler response takes a moment. This filler is frontend-controlled and does not change the transport-only role of Vapi.

## Local Browser Test

1. Start backend:

```bash
cd "/Users/vinay.paravastu/Downloads/personal projects/Final graduation project/apps/api"
source .venv/bin/activate
uvicorn main:app --port 8000
```

2. Start frontend:

```bash
cd "/Users/vinay.paravastu/Downloads/personal projects/Final graduation project/apps/web"
source ~/.nvm/nvm.sh
npm run dev
```

3. Open the frontend and go to Advisor -> Voice Scheduler.
4. Click Start Call.
5. Say: "I want to book a call about my SIP mandate."
6. Confirm:

- Transcript appears while speaking.
- Final transcript appears in the transcript history.
- Assistant response appears and is spoken.
- Booking code appears.
- Approval Centre shows pending calendar, notes, and email draft actions.

## Expected Demo Result

The voice call should generate a booking code and create three pending MCP actions. The Vapi assistant should not independently book, approve, send email, or bypass the backend scheduler endpoint.
