from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from services.google_sheets_logger import append_booking_log


def main():
    load_dotenv()
    rows = [
        {
            "booking_code": "KV-D101",
            "call_time": "2026-06-23 10:15:00 IST",
            "customer_topic": "exit load",
            "requested_slot": "Wednesday, June 24 at 11:00 AM",
            "assigned_advisor": "Asha Mehta",
            "status": "pending",
            "approval_status": "pending",
            "transcript_summary": "Customer requested an advisor call to understand exit load charges.",
        },
        {
            "booking_code": "KV-D102",
            "call_time": "2026-06-23 10:42:00 IST",
            "customer_topic": "redemption",
            "requested_slot": "Wednesday, June 24 at 2:30 PM",
            "assigned_advisor": "Rohan Iyer",
            "status": "pending",
            "approval_status": "pending",
            "transcript_summary": "Customer wanted help with redemption steps and requested an afternoon call.",
        },
        {
            "booking_code": "KV-D103",
            "call_time": "2026-06-23 11:05:00 IST",
            "customer_topic": "riskometer",
            "requested_slot": "Thursday, June 25 at 9:30 AM",
            "assigned_advisor": "Neha Kapoor",
            "status": "approved",
            "approval_status": "approved",
            "transcript_summary": "Customer asked for a call to interpret the fund riskometer before investing more.",
        },
        {
            "booking_code": "KV-D104",
            "call_time": "2026-06-23 11:48:00 IST",
            "customer_topic": "expense ratio",
            "requested_slot": "Friday, June 26 at 4:00 PM",
            "assigned_advisor": "Asha Mehta",
            "status": "completed",
            "approval_status": "completed",
            "transcript_summary": "Customer booked a follow-up call about expense ratio impact on returns.",
        },
        {
            "booking_code": "KV-D105",
            "call_time": "2026-06-23 12:20:00 IST",
            "customer_topic": "sip mandate",
            "requested_slot": "Monday, June 29 at 5:30 PM",
            "assigned_advisor": "Rohan Iyer",
            "status": "pending",
            "approval_status": "pending",
            "transcript_summary": "Customer wanted an advisor call to resolve a SIP mandate issue.",
        },
    ]

    results = []
    for row in rows:
        result = append_booking_log(row)
        results.append((row["booking_code"], result))

    print(f"Seeded {len(results)} rows at {datetime.now().isoformat(timespec='seconds')}")
    for booking_code, result in results:
        print(f"{booking_code}: {result['message']}")


if __name__ == "__main__":
    main()
