import json
import os
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:  # pragma: no cover - dependency may be installed later in local env
    gspread = None
    Credentials = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_BOOKING_LOG_PATH = PROJECT_ROOT / "data" / "outputs" / "booking_log.jsonl"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _credentials():
    if Credentials is None:
        return None
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if credentials_json:
        payload = json.loads(credentials_json)
        return Credentials.from_service_account_info(payload, scopes=SCOPES)
    if credentials_path:
        return Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return None


def _append_local_fallback(row):
    LOCAL_BOOKING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_BOOKING_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def append_booking_log(row):
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_BOOKING_SPREADSHEET_ID", "").strip()
    worksheet_name = os.getenv("GOOGLE_SHEETS_BOOKING_WORKSHEET", "Bookings").strip()
    credentials = _credentials()

    if not spreadsheet_id or credentials is None or gspread is None:
        _append_local_fallback(row)
        return {
            "logged": False,
            "provider": "local_fallback",
            "message": "Google Sheets not configured; saved booking log locally.",
        }

    client = gspread.authorize(credentials)
    workbook = client.open_by_key(spreadsheet_id)
    worksheet = workbook.worksheet(worksheet_name)
    worksheet.append_row(
        [
            row.get("booking_code", ""),
            row.get("call_time", ""),
            row.get("customer_topic", ""),
            row.get("requested_slot", ""),
            row.get("assigned_advisor", ""),
            row.get("status", ""),
            row.get("approval_status", ""),
            row.get("transcript_summary", ""),
        ],
        value_input_option="USER_ENTERED",
    )
    return {
        "logged": True,
        "provider": "google_sheets",
        "message": "Booking log appended to Google Sheets.",
        "worksheet": worksheet_name,
    }
