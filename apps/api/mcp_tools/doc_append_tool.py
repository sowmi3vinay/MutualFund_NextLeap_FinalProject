from datetime import datetime

from services.advisor_scheduler import get_booking_record
from services.google_sheets_logger import append_booking_log


def execute_doc_append(action):
    booking = get_booking_record(action.get("booking_code")) or {}
    details = action.get("details", {})
    log_result = append_booking_log(
        {
            "booking_code": action.get("booking_code"),
            "call_time": datetime.now().isoformat(timespec="seconds"),
            "customer_topic": booking.get("customer_topic") or details.get("customer_topic") or action.get("intent"),
            "requested_slot": action.get("slot"),
            "assigned_advisor": action.get("assigned_advisor") or details.get("assigned_advisor") or booking.get("advisor_name"),
            "status": booking.get("status", "pending"),
            "approval_status": booking.get("approval_status", action.get("status", "pending")),
            "transcript_summary": details.get("transcript_summary", ""),
        }
    )
    message = "Notes updated"
    if log_result["logged"]:
        message = "Notes updated and booking logged to Google Sheets"
    else:
        message = f"Notes updated; {log_result['message']}"
    return {
        "tool": "doc_append",
        "message": message,
        "booking_code": action.get("booking_code"),
        "details": details,
        "logging_result": log_result,
        "executed": True,
    }
