import json
import random
import re
import string
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEEKLY_PULSE_PATH = PROJECT_ROOT / "data" / "outputs" / "weekly_pulse.json"

MOCK_ADVISOR_SLOTS = [
    {"slot_id": "slot_001", "date": "Friday", "time": "3:00 PM", "available": True},
    {"slot_id": "slot_002", "date": "Monday", "time": "11:30 AM", "available": True},
    {"slot_id": "slot_003", "date": "Wednesday", "time": "4:30 PM", "available": True},
]

PII_DEFLECTION_REPLY = (
    "Please do not share personal details on this call. "
    "Please use the secure support channel instead."
)

_BOOKING_CODES = set()

PII_PATTERNS = {
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE),
    "aadhaar": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE),
    "phone_number": re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b"),
    "folio_number": re.compile(r"\bfolio(?:\s+number|\s+no\.?|\s*#)?\s*[:#-]?\s*[A-Z0-9/-]{5,}\b", re.IGNORECASE),
    "bank_details": re.compile(
        r"\b(?:account\s*(?:number|no\.?)|ifsc|bank\s*account)\s*[:#-]?\s*[A-Z0-9/-]{4,}\b",
        re.IGNORECASE,
    ),
}

INTENT_KEYWORDS = {
    "book_appointment": [
        "book a call",
        "schedule an advisor call",
        "book an appointment",
        "schedule a call",
        "advisor call",
        "appointment",
    ],
    "reschedule_appointment": [
        "reschedule",
        "move my appointment",
        "move appointment",
        "change my appointment",
        "shift my appointment",
        "friday afternoon",
    ],
    "call_preparation": [
        "what should i prepare",
        "documents should i keep ready",
        "what documents",
        "keep ready",
        "call preparation",
        "prepare for the call",
    ],
}

INTENT_PRIORITY = [
    "reschedule_appointment",
    "call_preparation",
    "book_appointment",
]


def get_weekly_pulse_top_theme():
    if not WEEKLY_PULSE_PATH.exists():
        return "mutual fund support questions"

    try:
        payload = json.loads(WEEKLY_PULSE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "mutual fund support questions"

    return payload.get("top_theme") or "mutual fund support questions"


def scheduler_greeting():
    top_theme = get_weekly_pulse_top_theme()
    theme_phrase = top_theme.replace(" / ", " and ").lower()
    return (
        "Welcome to the Mutual Fund Support Assistant.\n\n"
        f"One of the most common support topics this week has been {theme_phrase}.\n\n"
        "How can I help you today?"
    )


def contains_pii(transcript):
    return any(pattern.search(transcript or "") for pattern in PII_PATTERNS.values())


def detect_intent(transcript):
    transcript_lower = (transcript or "").lower()
    if contains_pii(transcript):
        return "pii_detected"

    for intent in INTENT_PRIORITY:
        keywords = INTENT_KEYWORDS[intent]
        if any(keyword in transcript_lower for keyword in keywords):
            return intent

    return "unknown"


def _slot_label(slot):
    return f"{slot['date']} {slot['time']}"


def choose_mock_slot(intent, transcript):
    transcript_lower = (transcript or "").lower()
    available_slots = [slot for slot in MOCK_ADVISOR_SLOTS if slot["available"]]
    if not available_slots:
        return None

    for slot in available_slots:
        if slot["date"].lower() in transcript_lower:
            return slot

    if intent == "reschedule_appointment" and "afternoon" in transcript_lower:
        return next((slot for slot in available_slots if "PM" in slot["time"]), available_slots[0])

    return available_slots[0]


def generate_booking_code():
    while True:
        code = f"KV-{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}"
        if code not in _BOOKING_CODES:
            _BOOKING_CODES.add(code)
            return code


def create_pending_mcp_actions(booking_code, slot_label, intent, transcript):
    from routes.approvals import _ACTIONS
    from services.mcp_orchestrator import create_pending_actions

    return create_pending_actions(
        _ACTIONS,
        booking_code=booking_code,
        slot=slot_label,
        intent=intent,
        transcript_summary=_safe_transcript_summary(transcript),
    )


def _safe_transcript_summary(transcript):
    summary = re.sub(r"\s+", " ", transcript or "").strip()
    if len(summary) > 140:
        return summary[:137].rstrip() + "..."
    return summary


def _preparation_reply():
    return (
        "For an advisor call, keep the scheme name, question topic, recent transaction date, "
        "and any non-sensitive support reference ready. Do not share PAN, Aadhaar, bank details, "
        "folio number, phone number, or email in this voice flow."
    )


def handle_voice_turn(transcript):
    greeting = scheduler_greeting()
    intent = detect_intent(transcript)

    if intent == "pii_detected":
        return {
            "reply": PII_DEFLECTION_REPLY,
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": MOCK_ADVISOR_SLOTS,
        }

    if intent == "call_preparation":
        return {
            "reply": _preparation_reply(),
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": MOCK_ADVISOR_SLOTS,
        }

    if intent in {"book_appointment", "reschedule_appointment"}:
        slot = choose_mock_slot(intent, transcript)
        slot_label = _slot_label(slot)
        booking_code = generate_booking_code()
        create_pending_mcp_actions(booking_code, slot_label, intent, transcript)
        action_text = "booked" if intent == "book_appointment" else "rescheduled"
        reply = (
            f"I can help with that. I have {action_text} a mock advisor slot for {slot_label}. "
            f"Your booking code is {booking_code}. I created pending approval actions for a calendar hold, "
            "notes entry, and advisor email draft."
        )
        return {
            "reply": reply,
            "booking_code": booking_code,
            "intent": intent,
            "slot": slot_label,
            "pending_actions_created": True,
            "greeting": greeting,
            "available_slots": MOCK_ADVISOR_SLOTS,
        }

    return {
        "reply": (
            "I can help book or reschedule an advisor call, or explain what to prepare for the call. "
            "Please tell me which one you need."
        ),
        "booking_code": None,
        "intent": intent,
        "slot": None,
        "pending_actions_created": False,
        "greeting": greeting,
        "available_slots": MOCK_ADVISOR_SLOTS,
    }
