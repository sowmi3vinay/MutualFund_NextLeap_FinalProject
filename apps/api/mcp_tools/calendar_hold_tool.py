import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_DURATION_MINUTES = 30
GOOGLE_CALENDAR_TEMPLATE_URL = "https://calendar.google.com/calendar/render"


def _next_weekday(day_name, timezone):
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    today = datetime.now(timezone).date()
    target_weekday = weekdays.get(day_name.lower(), today.weekday())
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _parse_slot(slot, timezone):
    match = re.search(
        r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b\s+(\d{1,2}):(\d{2})\s*(AM|PM)",
        slot or "",
        re.IGNORECASE,
    )
    if not match:
        start = datetime.now(timezone) + timedelta(days=1)
        return start.replace(hour=11, minute=0, second=0, microsecond=0)

    day_name, hour, minute, meridiem = match.groups()
    hour = int(hour)
    minute = int(minute)
    if meridiem.upper() == "PM" and hour != 12:
        hour += 12
    if meridiem.upper() == "AM" and hour == 12:
        hour = 0

    date = _next_weekday(day_name, timezone)
    return datetime(
        date.year,
        date.month,
        date.day,
        hour,
        minute,
        tzinfo=timezone,
    )


def _calendar_timestamp(value):
    return value.strftime("%Y%m%dT%H%M%S")


def _google_calendar_link(action):
    timezone_name = os.getenv("ADVISOR_TIMEZONE", DEFAULT_TIMEZONE)
    timezone = ZoneInfo(timezone_name)
    timezone_name = action.get("timezone") or action.get("details", {}).get("timezone") or timezone_name
    timezone = ZoneInfo(timezone_name)
    slot_start_iso = action.get("slot_start_iso") or action.get("details", {}).get("slot_start_iso")
    slot_end_iso = action.get("slot_end_iso") or action.get("details", {}).get("slot_end_iso")
    if slot_start_iso:
        start = datetime.fromisoformat(slot_start_iso)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone)
        else:
            start = start.astimezone(timezone)
    else:
        start = _parse_slot(action.get("slot"), timezone)

    if slot_end_iso:
        end = datetime.fromisoformat(slot_end_iso)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone)
        else:
            end = end.astimezone(timezone)
    else:
        end = start + timedelta(minutes=int(os.getenv("ADVISOR_SLOT_MINUTES", DEFAULT_DURATION_MINUTES)))
    booking_code = action.get("booking_code")
    intent = action.get("intent") or action.get("details", {}).get("intent") or "advisor_call"
    title = f"Advisor Call Hold - {booking_code}"
    details = "\n".join(
        [
            "Tentative advisor appointment hold.",
            f"Booking code: {booking_code}",
            f"Intent: {intent}",
            "Do not add customer personal details unless provided through the secure confirmation flow.",
        ]
    )
    query = urlencode(
        {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{_calendar_timestamp(start)}/{_calendar_timestamp(end)}",
            "details": details,
            "ctz": timezone_name,
        }
    )
    return f"{GOOGLE_CALENDAR_TEMPLATE_URL}?{query}", start, end, timezone_name


def execute_calendar_hold(action):
    calendar_link, start, end, timezone_name = _google_calendar_link(action)
    return {
        "tool": "calendar_hold",
        "message": "Google Calendar event link created",
        "booking_code": action.get("booking_code"),
        "slot": action.get("slot"),
        "calendar_link": calendar_link,
        "calendar_provider": "google_calendar_link",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": timezone_name,
        "executed": True,
    }
