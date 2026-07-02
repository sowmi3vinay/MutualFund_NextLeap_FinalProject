import json
import os
import random
import re
import string
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from services.advisor_scheduler import find_available_advisor, reserve_booking

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEEKLY_PULSE_PATH = PROJECT_ROOT / "data" / "outputs" / "weekly_pulse.json"

BUSINESS_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DEFAULT_BUSINESS_START_HOUR = 9
DEFAULT_BUSINESS_END_HOUR = 18
DEFAULT_SLOT_INTERVAL_MINUTES = 30
DEFAULT_SLOT_DURATION_MINUTES = 30
DEFAULT_SLOT_HORIZON_DAYS = 14
DEFAULT_TIMEZONE = "Asia/Kolkata"

PII_DEFLECTION_REPLY = (
    "Please do not share personal details on this call. "
    "Please use the secure support channel instead."
)

ADVICE_DEFLECTION_REPLY = (
    "I cannot recommend the best mutual fund, compare fund performance, or predict returns in this voice flow. "
    "I can help book an advisor call for a factual discussion or explain what to prepare for that call."
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
    "available_slots": [
        "available",
        "availability",
        "available slots",
        "what times",
        "which slots",
        "show slots",
        "time slots",
        "available time",
    ],
    "book_appointment": [
        "book",
        "schedule",
        "book a call",
        "schedule an advisor call",
        "schedule an adviser call",
        "book an appointment",
        "schedule a call",
        "advisor call",
        "adviser call",
        "consultation",
        "tentative time",
        "hold a time",
        "visit call",
        "appointment",
    ],
    "reschedule_appointment": [
        "reschedule",
        "not available",
        "unavailable",
        "cannot make",
        "can't make",
        "can you do it",
        "do it on",
        "move it",
        "move my appointment",
        "move appointment",
        "change my appointment",
        "shift my appointment",
        "friday afternoon",
        "saturday morning",
        "sunday afternoon",
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

ADVICE_KEYWORDS = [
    "best mutual fund",
    "best performing",
    "performing",
    "performance",
    "compare",
    "compared to",
    "suggest which",
    "recommend",
    "highest return",
    "future return",
]

SUPPORT_TOPIC_KEYWORDS = [
    "exit load",
    "redeem",
    "redemption",
    "riskometer",
    "benchmark",
    "expense ratio",
    "fees",
    "sip",
    "mandate",
    "folio",
    "statement",
]

INTENT_PRIORITY = [
    "reschedule_appointment",
    "call_preparation",
    "available_slots",
    "book_appointment",
]

DAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

TIME_WINDOWS = ["morning", "afternoon", "evening"]
RELATIVE_DATE_TERMS = [
    "today",
    "tomorrow",
    "day after tomorrow",
    "next few days",
    "next 3 days",
    "next three days",
]
MONTH_NAMES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
TIME_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty one": 21,
    "twenty two": 22,
    "twenty three": 23,
}

SCHEDULING_SIGNAL_TERMS = [
    "book",
    "booked",
    "booking",
    "schedule",
    "scheduled",
    "reschedule",
    "appointment",
    "call",
    "slot",
    "advisor",
    "adviser",
]


def _normalize_transcript(transcript):
    normalized = re.sub(r"\s+", " ", transcript or "").strip()
    if not normalized:
        return ""
    replacements = {
        "after tomorrow": "day after tomorrow",
        "advisor": "advisor",
        "adviser": "adviser",
    }
    lowered = normalized.lower()
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    return lowered


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _business_days():
    configured_days = os.getenv("ADVISOR_BUSINESS_DAYS")
    if not configured_days:
        return BUSINESS_DAYS
    days = [day.strip().title() for day in configured_days.split(",") if day.strip()]
    return days or BUSINESS_DAYS


def _business_days_label():
    days = _business_days()
    default_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if days == default_days:
        return "Monday to Friday"
    return ", ".join(days)


def _advisor_timezone():
    return ZoneInfo(os.getenv("ADVISOR_TIMEZONE", DEFAULT_TIMEZONE))


def _now():
    return datetime.now(_advisor_timezone())


def _format_time(hour, minute):
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def _format_date(value):
    return value.strftime("%A, %B %-d")


def _slot_duration_minutes():
    return _env_int("ADVISOR_SLOT_MINUTES", DEFAULT_SLOT_DURATION_MINUTES)


def available_advisor_slots():
    start_hour = _env_int("ADVISOR_BUSINESS_START_HOUR", DEFAULT_BUSINESS_START_HOUR)
    end_hour = _env_int("ADVISOR_BUSINESS_END_HOUR", DEFAULT_BUSINESS_END_HOUR)
    interval = _env_int("ADVISOR_SLOT_INTERVAL_MINUTES", DEFAULT_SLOT_INTERVAL_MINUTES)
    horizon_days = _env_int("ADVISOR_SLOT_HORIZON_DAYS", DEFAULT_SLOT_HORIZON_DAYS)
    interval = interval if interval > 0 else DEFAULT_SLOT_INTERVAL_MINUTES
    horizon_days = horizon_days if horizon_days > 0 else DEFAULT_SLOT_HORIZON_DAYS
    timezone = _advisor_timezone()
    now = _now()
    today = now.date()
    business_days = {day.lower() for day in _business_days()}

    slots = []
    slot_index = 1
    for day_offset in range(0, horizon_days):
        slot_date = today + timedelta(days=day_offset)
        day_name = slot_date.strftime("%A")
        if day_name.lower() not in business_days:
            continue
        for total_minutes in range(start_hour * 60, end_hour * 60, interval):
            hour = total_minutes // 60
            minute = total_minutes % 60
            start = datetime(slot_date.year, slot_date.month, slot_date.day, hour, minute, tzinfo=timezone)
            if start <= now:
                continue
            end = start + timedelta(minutes=_slot_duration_minutes())
            slots.append(
                {
                    "slot_id": f"slot_{slot_index:03d}",
                    "date": slot_date.isoformat(),
                    "day": day_name,
                    "display_date": _format_date(slot_date),
                    "time": _format_time(hour, minute),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "timezone": str(timezone),
                    "available": True,
                }
            )
            slot_index += 1
    return slots


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
        "Welcome to the Mutual Fund Support Assistant. "
        f"This week, a common support topic is {theme_phrase}. "
        "How can I help?"
    )


def contains_pii(transcript):
    return any(pattern.search(transcript or "") for pattern in PII_PATTERNS.values())


def is_advice_or_performance_request(transcript):
    transcript_lower = (transcript or "").lower()
    if any(keyword in transcript_lower for keyword in ADVICE_KEYWORDS):
        return True

    mentions_fund = "fund" in transcript_lower or "mutual fund" in transcript_lower
    asks_best = any(term in transcript_lower for term in ["best", "top", "better", "should i"])
    asks_performance = any(term in transcript_lower for term in ["perform", "return", "compare", "versus", "vs"])
    return mentions_fund and (asks_best or asks_performance)


def is_greeting_or_mic_check(transcript):
    transcript_lower = _normalize_transcript(transcript)
    if not transcript_lower:
        return False

    if any(term in transcript_lower for term in SCHEDULING_SIGNAL_TERMS + SUPPORT_TOPIC_KEYWORDS + DAY_NAMES + TIME_WINDOWS):
        return False

    exact_phrases = {
        "hello",
        "hey",
        "hi",
        "can you hear me",
        "are you there",
        "hello are you there",
        "hey are you there",
        "hi are you there",
    }
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", transcript_lower)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned in exact_phrases


def is_advisor_topic_question(transcript):
    transcript_lower = _normalize_transcript(transcript)
    if re.search(
        r"\bwhat(?:\s+are)?\s+(?:the\s+)?topics?\s+(?:which\s+)?(?:you\s+)?can\s+help(?:\s+me)?\s+with\b",
        transcript_lower,
    ):
        return True
    return any(
        phrase in transcript_lower
        for phrase in [
            "what topics",
            "which topics",
            "what all topics",
            "what can you help me with",
            "what can you help with",
            "which topics can you help",
            "which topics you can help",
            "what can you do",
            "how can you help",
            "what can adviser help",
            "what can advisor help",
            "topics adviser can help",
            "topics advisor can help",
            "range of topics",
        ]
    )


def is_support_topic_discussion(transcript):
    transcript_lower = _normalize_transcript(transcript)
    return any(keyword in transcript_lower for keyword in SUPPORT_TOPIC_KEYWORDS)


def detect_intent(transcript):
    transcript_lower = _normalize_transcript(transcript)
    if contains_pii(transcript):
        return "pii_detected"

    if is_greeting_or_mic_check(transcript):
        return "greeting_or_mic_check"

    if is_advisor_topic_question(transcript):
        return "advisor_topic_question"

    if is_advice_or_performance_request(transcript):
        return "advice_or_performance_request"

    mentions_day_or_time = any(term in transcript_lower for term in DAY_NAMES + TIME_WINDOWS + RELATIVE_DATE_TERMS)
    mentions_day_or_time = mentions_day_or_time or _requested_date(transcript) is not None
    mentions_day_or_time = mentions_day_or_time or _requested_date_range_days(transcript) is not None
    if mentions_day_or_time and any(
        phrase in transcript_lower
        for phrase in ["not available", "unavailable", "can you do", "do it", "move", "change", "shift"]
    ):
        return "reschedule_appointment"

    if mentions_day_or_time and not any(keyword in transcript_lower for keyword in INTENT_KEYWORDS["book_appointment"]):
        return "reschedule_appointment"

    for intent in INTENT_PRIORITY:
        keywords = INTENT_KEYWORDS[intent]
        if any(keyword in transcript_lower for keyword in keywords):
            return intent

    if is_support_topic_discussion(transcript):
        return "support_topic_discussion"

    return "unknown"


def _slot_label(slot):
    return f"{slot['display_date']} at {slot['time']}"


def _available_slot_labels():
    return [_slot_label(slot) for slot in available_advisor_slots() if slot["available"]]


def _available_slots_reply():
    start_hour = _env_int("ADVISOR_BUSINESS_START_HOUR", DEFAULT_BUSINESS_START_HOUR)
    end_hour = _env_int("ADVISOR_BUSINESS_END_HOUR", DEFAULT_BUSINESS_END_HOUR)
    interval = _env_int("ADVISOR_SLOT_INTERVAL_MINUTES", DEFAULT_SLOT_INTERVAL_MINUTES)
    return (
        f"Advisor slots are open {_business_days_label()}, "
        f"{_format_time(start_hour, 0)} to {_format_time(end_hour, 0)}, every {interval} minutes."
    )


def _outside_booking_hours_reply(requested_date):
    start_hour = _env_int("ADVISOR_BUSINESS_START_HOUR", DEFAULT_BUSINESS_START_HOUR)
    end_hour = _env_int("ADVISOR_BUSINESS_END_HOUR", DEFAULT_BUSINESS_END_HOUR)
    return (
        f"{_format_date(requested_date)} is outside advisor hours. "
        f"Please choose {_business_days_label()}, "
        f"{_format_time(start_hour, 0)} to {_format_time(end_hour, 0)}."
    )


def _specific_time_options_reply(requested_date, window):
    matching_slots = [
        slot
        for slot in available_advisor_slots()
        if slot["available"]
        and slot["date"] == requested_date.isoformat()
        and _slot_matches_window(slot, window)
    ]
    options = ", ".join(slot["time"] for slot in matching_slots[:3])
    window_label = f" {window}" if window else ""
    if options:
        return f"{_format_date(requested_date)}{window_label} is available. Please choose a time, for example {options}."
    return f"{_format_date(requested_date)}{window_label} is not available. {_available_slots_reply()}"


def _spoken_booking_code(booking_code):
    if not booking_code:
        return None
    parts = []
    for character in booking_code:
        if character == "-":
            parts.append("dash")
        elif character.isalpha():
            parts.append(character.upper())
        elif character.isdigit():
            parts.append(character)
    return " ".join(parts)


def _with_spoken_reply(payload, spoken_reply=None):
    payload["spoken_reply"] = spoken_reply or payload["reply"]
    return payload


def _requested_day(transcript):
    transcript_lower = _normalize_transcript(transcript)
    matches = [
        (transcript_lower.rfind(day), day)
        for day in DAY_NAMES
        if day in transcript_lower
    ]
    if not matches:
        return None
    return max(matches)[1]


def _next_date_for_weekday(day_name, include_today=True):
    weekdays = {day: index for index, day in enumerate(DAY_NAMES)}
    today = _now().date()
    target_weekday = weekdays[day_name]
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0 and not include_today:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _requested_date_range_days(transcript):
    transcript_lower = _normalize_transcript(transcript)
    if "next few days" in transcript_lower:
        return 3

    match = re.search(r"\b(?:next|coming)\s+(\d+|one|two|three|four|five|six|seven)\s+days\b", transcript_lower)
    if not match:
        match = re.search(r"\b(?:within|over)\s+the\s+next\s+(\d+|one|two|three|four|five|six|seven)\s+days\b", transcript_lower)
    if not match:
        return None

    value = match.group(1)
    if value.isdigit():
        return int(value)
    return TIME_WORDS.get(value)


def _requested_date(transcript):
    transcript_lower = _normalize_transcript(transcript)
    today = _now().date()

    if "day after tomorrow" in transcript_lower:
        return today + timedelta(days=2)
    if "tomorrow" in transcript_lower:
        return today + timedelta(days=1)
    if "today" in transcript_lower:
        return today

    match = re.search(r"\bin\s+(\d+|one|two|three|four|five|six|seven)\s+days?\b", transcript_lower)
    if match:
        value = match.group(1)
        offset = int(value) if value.isdigit() else TIME_WORDS.get(value)
        if offset is not None:
            return today + timedelta(days=offset)

    month_pattern = "|".join(MONTH_NAMES.keys())
    match = re.search(rf"\b({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", transcript_lower)
    if not match:
        match = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})\b", transcript_lower)
        if match:
            day = int(match.group(1))
            month = MONTH_NAMES[match.group(2)]
        else:
            day = None
            month = None
    else:
        month = MONTH_NAMES[match.group(1)]
        day = int(match.group(2))

    if month and day:
        year = today.year
        try:
            requested = today.replace(year=year, month=month, day=day)
        except ValueError:
            return None
        if requested < today:
            try:
                requested = requested.replace(year=year + 1)
            except ValueError:
                return None
        return requested

    requested_day = _requested_day(transcript)
    if requested_day:
        return _next_date_for_weekday(requested_day, include_today=True)

    return None


def _requested_window(transcript):
    transcript_lower = _normalize_transcript(transcript)
    matches = [
        (transcript_lower.rfind(window), window)
        for window in TIME_WINDOWS
        if window in transcript_lower
    ]
    if not matches:
        return None
    return max(matches)[1]


def _requested_time_minutes(transcript):
    transcript_lower = _normalize_transcript(transcript)
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", transcript_lower)
    if not match:
        match = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(am|pm)\b",
            transcript_lower,
        )
        if match:
            hour = TIME_WORDS[match.group(1)]
            minute = 0
            meridiem = match.group(2)
        else:
            hour = None
            minute = 0
            meridiem = None
    else:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)

    if meridiem:
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return hour * 60 + minute

    if _requested_window(transcript):
        for phrase, phrase_hour in sorted(TIME_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(phrase)}\b", transcript_lower):
                return phrase_hour * 60
        standalone_hour = re.search(r"\b([01]?\d|2[0-3])\b", transcript_lower)
        if standalone_hour:
            return int(standalone_hour.group(1)) * 60

    return None


def _has_requested_slot_preference(transcript):
    return bool(
        _requested_date(transcript)
        or _requested_date_range_days(transcript)
        or _requested_window(transcript)
        or _requested_time_minutes(transcript) is not None
    )


def _is_business_date(value):
    return value.strftime("%A").lower() in {day.lower() for day in _business_days()}


def _requested_date_range_slots(transcript):
    days = _requested_date_range_days(transcript)
    if not days:
        return []
    today = _now().date()
    end_date = today + timedelta(days=days)
    return [
        slot
        for slot in available_advisor_slots()
        if today <= datetime.fromisoformat(slot["date"]).date() <= end_date
    ]


def _range_slots_reply(transcript):
    slots = _requested_date_range_slots(transcript)
    if not slots:
        return f"No advisor slots are available in that date range. {_available_slots_reply()}"
    options = ", ".join(_slot_label(slot) for slot in slots[:3])
    return f"Available options include {options}. Which time should I hold?"


def _time_outside_hours_reply(requested_date, requested_time):
    hour = requested_time // 60
    minute = requested_time % 60
    start_hour = _env_int("ADVISOR_BUSINESS_START_HOUR", DEFAULT_BUSINESS_START_HOUR)
    end_hour = _env_int("ADVISOR_BUSINESS_END_HOUR", DEFAULT_BUSINESS_END_HOUR)
    return (
        f"{_format_date(requested_date)} at {_format_time(hour, minute)} is outside advisor hours. "
        f"Please choose {_business_days_label()}, "
        f"{_format_time(start_hour, 0)} to {_format_time(end_hour, 0)}."
    )


def _requested_exact_slot_available(requested_date, requested_time):
    if requested_date is None or requested_time is None:
        return True
    return any(
        slot["date"] == requested_date.isoformat() and _slot_time_minutes(slot) == requested_time
        for slot in available_advisor_slots()
    )


def _explicit_reschedule_requested(transcript):
    transcript_lower = _normalize_transcript(transcript)
    return any(
        phrase in transcript_lower
        for phrase in [
            "reschedule",
            "not available",
            "unavailable",
            "cannot make",
            "can't make",
            "move",
            "change",
            "shift",
        ]
    )


def _slot_time_minutes(slot):
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", slot["time"])
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(3)
    if meridiem == "PM" and hour != 12:
        hour += 12
    if meridiem == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _slot_matches_window(slot, requested_window):
    if not requested_window:
        return True
    slot_time = slot["time"].upper()
    slot_minutes = _slot_time_minutes(slot)
    if requested_window == "morning":
        return slot_minutes is not None and slot_minutes < 12 * 60
    if requested_window == "afternoon":
        return slot_minutes is not None and 12 * 60 <= slot_minutes < 16 * 60
    if requested_window == "evening":
        return slot_minutes is not None and 16 * 60 <= slot_minutes < 18 * 60
    return True


def choose_advisor_slot(intent, transcript):
    available_slots = [slot for slot in available_advisor_slots() if slot["available"]]
    if not available_slots:
        return None

    requested_date = _requested_date(transcript)
    range_slots = _requested_date_range_slots(transcript)
    requested_window = _requested_window(transcript)
    requested_time = _requested_time_minutes(transcript)

    if requested_date:
        date_matches = [slot for slot in available_slots if slot["date"] == requested_date.isoformat()]
        exact_time_matches = [
            slot for slot in date_matches if requested_time is not None and _slot_time_minutes(slot) == requested_time
        ]
        if exact_time_matches:
            return exact_time_matches[0]
        exact_matches = [slot for slot in date_matches if _slot_matches_window(slot, requested_window)]
        if exact_matches:
            return exact_matches[0]
        if date_matches:
            return date_matches[0]

    if range_slots:
        exact_time_matches = [
            slot for slot in range_slots if requested_time is not None and _slot_time_minutes(slot) == requested_time
        ]
        if exact_time_matches:
            return exact_time_matches[0]
        window_matches = [slot for slot in range_slots if _slot_matches_window(slot, requested_window)]
        if window_matches:
            return window_matches[0]
        return range_slots[0]

    if requested_time is not None:
        exact_time_matches = [slot for slot in available_slots if _slot_time_minutes(slot) == requested_time]
        if exact_time_matches:
            return exact_time_matches[0]

    if intent == "reschedule_appointment" and requested_window:
        window_matches = [slot for slot in available_slots if _slot_matches_window(slot, requested_window)]
        if window_matches:
            return window_matches[0]

    return available_slots[0]


def generate_booking_code():
    while True:
        code = f"KV-{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}"
        if code not in _BOOKING_CODES:
            _BOOKING_CODES.add(code)
            return code


def create_pending_mcp_actions(booking_code, slot, assigned_advisor, intent, transcript):
    from routes.approvals import _ACTIONS
    from services.mcp_orchestrator import create_pending_actions

    slot_label = _slot_label(slot)
    return create_pending_actions(
        _ACTIONS,
        booking_code=booking_code,
        slot=slot_label,
        assigned_advisor=assigned_advisor,
        intent=intent,
        transcript_summary=_safe_transcript_summary(transcript),
        customer_topic=_customer_topic(transcript),
        slot_start_iso=slot.get("start"),
        slot_end_iso=slot.get("end"),
        timezone=slot.get("timezone"),
    )


def _safe_transcript_summary(transcript):
    summary = re.sub(r"\s+", " ", transcript or "").strip()
    if len(summary) > 140:
        return summary[:137].rstrip() + "..."
    return summary


def _customer_topic(transcript):
    transcript_lower = _normalize_transcript(transcript)
    for keyword in SUPPORT_TOPIC_KEYWORDS:
        if keyword in transcript_lower:
            return keyword
    if "mutual fund" in transcript_lower:
        return "mutual fund support"
    return "advisor support"


def _preparation_reply():
    return (
        "Keep the scheme name, question topic, and recent transaction date ready. "
        "Please do not share PAN, bank details, folio number, phone, or email on this call."
    )


def _advisor_topics_reply():
    return (
        "An advisor can help with exit load, redemption steps, fees, benchmarks, riskometer, "
        "statements, and SIP questions. If you want a call, please share a weekday and time."
    )


def _support_topic_reply():
    return "I can help book an advisor call for that topic. What weekday and time works?"


def _schedule_day_time_reply():
    return "Sure. What weekday and time work for you?"


def _unknown_reply():
    return (
        "I can help with advisor-call booking for exit load, redemption steps, fees, benchmarks, "
        "riskometer, statements, and SIP questions. Please tell me a weekday and time if you want a call."
    )


def _looks_like_scheduling_request(transcript):
    transcript_lower = _normalize_transcript(transcript)
    return any(term in transcript_lower for term in SCHEDULING_SIGNAL_TERMS)


def handle_voice_turn(transcript):
    transcript = re.sub(r"\s+", " ", transcript or "").strip()
    greeting = scheduler_greeting()
    intent = detect_intent(transcript)
    available_slots = available_advisor_slots()
    requested_date = _requested_date(transcript)
    requested_range_days = _requested_date_range_days(transcript)
    requested_time = _requested_time_minutes(transcript)

    if intent == "greeting_or_mic_check":
        return _with_spoken_reply({
            "reply": "Yes, I can hear you. How can I help?",
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent == "pii_detected":
        return _with_spoken_reply({
            "reply": PII_DEFLECTION_REPLY,
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent == "call_preparation":
        return _with_spoken_reply({
            "reply": _preparation_reply(),
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent == "advisor_topic_question":
        return _with_spoken_reply({
            "reply": _advisor_topics_reply(),
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent == "support_topic_discussion":
        return _with_spoken_reply({
            "reply": _support_topic_reply(),
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent == "available_slots":
        if requested_range_days:
            reply = _range_slots_reply(transcript)
        elif requested_date:
            reply = (
                _specific_time_options_reply(requested_date, _requested_window(transcript))
                if _is_business_date(requested_date)
                else _outside_booking_hours_reply(requested_date)
            )
        else:
            reply = _available_slots_reply()
        return _with_spoken_reply({
            "reply": reply,
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent == "advice_or_performance_request":
        return _with_spoken_reply({
            "reply": ADVICE_DEFLECTION_REPLY,
            "booking_code": None,
            "intent": intent,
            "slot": None,
            "pending_actions_created": False,
            "greeting": greeting,
            "available_slots": available_slots,
        })

    if intent in {"book_appointment", "reschedule_appointment"}:
        if not _has_requested_slot_preference(transcript):
            return _with_spoken_reply({
                "reply": _support_topic_reply()
                if is_support_topic_discussion(transcript)
                else _schedule_day_time_reply(),
                "booking_code": None,
                "intent": "support_topic_discussion" if is_support_topic_discussion(transcript) else intent,
                "slot": None,
                "pending_actions_created": False,
                "greeting": greeting,
                "available_slots": available_slots,
            })
        if requested_date and not _is_business_date(requested_date):
            return _with_spoken_reply({
                "reply": _outside_booking_hours_reply(requested_date),
                "booking_code": None,
                "intent": intent,
                "slot": None,
                "pending_actions_created": False,
                "greeting": greeting,
                "available_slots": available_slots,
            })
        if requested_date and requested_time is not None and not _requested_exact_slot_available(requested_date, requested_time):
            return _with_spoken_reply({
                "reply": _time_outside_hours_reply(requested_date, requested_time),
                "booking_code": None,
                "intent": intent,
                "slot": None,
                "pending_actions_created": False,
                "greeting": greeting,
                "available_slots": available_slots,
            })
        if requested_range_days and _requested_time_minutes(transcript) is None:
            return _with_spoken_reply({
                "reply": _range_slots_reply(transcript),
                "booking_code": None,
                "intent": "available_slots",
                "slot": None,
                "pending_actions_created": False,
                "greeting": greeting,
                "available_slots": available_slots,
            })
        if requested_date and _requested_time_minutes(transcript) is None:
            return _with_spoken_reply({
                "reply": _specific_time_options_reply(requested_date, _requested_window(transcript)),
                "booking_code": None,
                "intent": "available_slots",
                "slot": None,
                "pending_actions_created": False,
                "greeting": greeting,
                "available_slots": available_slots,
            })
        slot = choose_advisor_slot(intent, transcript)
        assigned_advisor = find_available_advisor(slot)
        if assigned_advisor is None:
            return _with_spoken_reply({
                "reply": f"{_slot_label(slot)} is no longer available. Please choose another time on {_business_days_label()}.",
                "booking_code": None,
                "intent": "available_slots",
                "slot": None,
                "pending_actions_created": False,
                "greeting": greeting,
                "available_slots": available_slots,
            })
        slot_label = _slot_label(slot)
        booking_code = generate_booking_code()
        customer_topic = _customer_topic(transcript)
        transcript_summary = _safe_transcript_summary(transcript)
        reserve_booking(booking_code, slot, assigned_advisor, intent, transcript_summary, customer_topic)
        create_pending_mcp_actions(booking_code, slot, assigned_advisor["name"], intent, transcript)
        action_text = "moved" if _explicit_reschedule_requested(transcript) else "held"
        spoken_code = _spoken_booking_code(booking_code)
        reply = (
            f"Tentative advisor slot {action_text} for {slot_label} with {assigned_advisor['name']}. "
            f"Booking code: {booking_code}. Approval is pending."
        )
        spoken_reply = (
            f"Tentative advisor slot {action_text} for {slot_label} with {assigned_advisor['name']}. "
            f"Your booking code is {spoken_code}. Approval is pending."
        )
        return _with_spoken_reply({
            "reply": reply,
            "booking_code": booking_code,
            "intent": intent,
            "slot": slot_label,
            "assigned_advisor": assigned_advisor["name"],
            "pending_actions_created": True,
            "greeting": greeting,
            "available_slots": available_slots,
        }, spoken_reply)

    return _with_spoken_reply({
        "reply": _schedule_day_time_reply() if _looks_like_scheduling_request(transcript) else _unknown_reply(),
        "booking_code": None,
        "intent": intent,
        "slot": None,
        "pending_actions_created": False,
        "greeting": greeting,
        "available_slots": available_slots,
    })
