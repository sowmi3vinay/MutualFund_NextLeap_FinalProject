import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BOOKING_STORE_PATH = PROJECT_ROOT / "data" / "outputs" / "advisor_bookings.json"

ADVISOR_ROSTER = [
    {"advisor_id": "ADV-001", "name": "Asha Mehta"},
    {"advisor_id": "ADV-002", "name": "Rohan Iyer"},
    {"advisor_id": "ADV-003", "name": "Neha Kapoor"},
]

ACTIVE_BOOKING_STATUSES = {"pending", "approved", "completed"}


def list_advisors():
    return ADVISOR_ROSTER


def _load_bookings():
    if not BOOKING_STORE_PATH.exists():
        return []
    try:
        return json.loads(BOOKING_STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_bookings(bookings):
    BOOKING_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOOKING_STORE_PATH.write_text(json.dumps(bookings, indent=2), encoding="utf-8")


def _is_conflict(existing_booking, slot, advisor_name):
    if existing_booking.get("advisor_name") != advisor_name:
        return False
    if existing_booking.get("status") not in ACTIVE_BOOKING_STATUSES:
        return False
    return existing_booking.get("slot_start_iso") == slot.get("start")


def find_available_advisor(slot):
    bookings = _load_bookings()
    for advisor in ADVISOR_ROSTER:
        if any(_is_conflict(booking, slot, advisor["name"]) for booking in bookings):
            continue
        return advisor
    return None


def reserve_booking(booking_code, slot, advisor, intent, transcript_summary, customer_topic):
    bookings = _load_bookings()
    record = {
        "booking_code": booking_code,
        "advisor_id": advisor["advisor_id"],
        "advisor_name": advisor["name"],
        "slot": f"{slot['display_date']} at {slot['time']}",
        "slot_start_iso": slot.get("start"),
        "slot_end_iso": slot.get("end"),
        "timezone": slot.get("timezone"),
        "intent": intent,
        "customer_topic": customer_topic,
        "transcript_summary": transcript_summary,
        "status": "pending",
        "approval_status": "pending",
    }
    bookings = [booking for booking in bookings if booking.get("booking_code") != booking_code]
    bookings.append(record)
    _save_bookings(bookings)
    return record


def update_booking_status(booking_code, *, status=None, approval_status=None):
    bookings = _load_bookings()
    updated = None
    for booking in bookings:
        if booking.get("booking_code") != booking_code:
            continue
        if status:
            booking["status"] = status
        if approval_status:
            booking["approval_status"] = approval_status
        updated = booking
        break
    if updated is not None:
        _save_bookings(bookings)
    return updated


def get_booking_record(booking_code):
    return next((booking for booking in _load_bookings() if booking.get("booking_code") == booking_code), None)
