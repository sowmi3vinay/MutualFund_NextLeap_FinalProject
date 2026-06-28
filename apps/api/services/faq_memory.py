import re
import threading
from datetime import datetime
from uuid import uuid4

MAX_TURNS_PER_THREAD = 12

SCHEME_ALIASES = {
    "HDFC ELSS Tax Saver": [
        "hdfc elss tax saver",
        "elss tax saver",
        "hdfc elss tax saver fund",
        "hdfc elss",
        "selected elss fund",
        "elss fund",
    ],
    "HDFC Flexi Cap Fund": [
        "hdfc flexi cap fund",
        "hdfc flexicap fund",
        "hdfc flexi cap",
        "hdfc flexicap",
        "flexi cap fund",
        "flexicap fund",
        "selected flexi cap fund",
    ],
    "HDFC Balanced Advantage Fund": [
        "hdfc balanced advantage fund",
        "balanced advantage fund",
    ],
    "HDFC Mid-Cap Opportunities Fund": [
        "hdfc mid-cap opportunities fund",
        "hdfc mid cap opportunities fund",
        "hdfc mid cap",
        "hdfc mid-cap",
        "hdfc mid cap fund",
        "hdfc mid-cap fund",
        "hdfc midcap fund",
        "mid cap fund",
        "midcap fund",
        "mid-cap opportunities fund",
        "mid cap opportunities fund",
    ],
    "HDFC Small Cap Fund": [
        "hdfc small cap fund",
        "hdfc smallcap fund",
        "hdfc small cap",
        "hdfc smallcap",
        "small cap fund",
        "smallcap fund",
    ],
}

TOPIC_ALIASES = {
    "exit load": ["exit load", "load", "charged"],
    "expense ratio": ["expense ratio", "expenses", "fee", "fees"],
    "benchmark": ["benchmark"],
    "riskometer": ["riskometer", "risk"],
    "minimum SIP": ["minimum sip", "sip minimum", "minimum amount"],
    "capital gains statement": ["capital gains", "tax statement", "statement"],
}

_MEMORY_LOCK = threading.RLock()
_SESSIONS = {}


def create_session_id():
    return f"faq-{uuid4().hex[:12]}"


def _thread_key(thread_id):
    return thread_id or "default"


def _now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _ensure_thread(session_id, thread_id):
    session_key = session_id or create_session_id()
    thread_key = _thread_key(thread_id)
    with _MEMORY_LOCK:
        session = _SESSIONS.setdefault(session_key, {})
        thread = session.setdefault(
            thread_key,
            {
                "turns": [],
                "last_scheme": None,
                "last_topic": None,
                "created_at": _now(),
                "updated_at": _now(),
            },
        )
    return session_key, thread_key, thread


def detect_scheme(text):
    lowered = (text or "").lower()
    for scheme, aliases in SCHEME_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return scheme
    return None


def detect_topic(text):
    lowered = (text or "").lower()
    for topic, aliases in TOPIC_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return topic
    return None


def contextualize_question(question, session_id=None, thread_id=None):
    session_key, thread_key, thread = _ensure_thread(session_id, thread_id)
    question_text = (question or "").strip()
    detected_scheme = detect_scheme(question_text)
    detected_topic = detect_topic(question_text)

    with _MEMORY_LOCK:
        last_scheme = thread.get("last_scheme")
        last_topic = thread.get("last_topic")

    scheme_for_query = detected_scheme or last_scheme
    topic_for_query = detected_topic or last_topic

    additions = []
    use_memory = _looks_contextual(question_text)
    if use_memory and scheme_for_query and not detected_scheme:
        additions.append(f"For {scheme_for_query}.")
    if use_memory and topic_for_query and not detected_topic:
        additions.append(f"The topic is {topic_for_query}.")

    if additions:
        rewritten_question = f"{question_text} {' '.join(additions)}"
    else:
        rewritten_question = question_text

    return {
        "session_id": session_key,
        "thread_id": thread_key,
        "question": question_text,
        "rewritten_question": rewritten_question,
        "detected_scheme": detected_scheme,
        "detected_topic": detected_topic,
        "last_scheme": scheme_for_query,
        "last_topic": topic_for_query,
    }


def _looks_contextual(question):
    lowered = question.lower()
    return bool(
        re.search(r"\b(it|its|that|this|same|selected|above|previous)\b", lowered)
        or len(re.findall(r"[a-z0-9]+", lowered)) <= 5
    )


def remember_turn(session_id, thread_id, question, answer, citations=None):
    session_key, thread_key, thread = _ensure_thread(session_id, thread_id)
    scheme = detect_scheme(question)
    topic = detect_topic(question)
    use_memory = _looks_contextual(question)
    turn = {
        "question": question,
        "answer": answer,
        "citations": citations or [],
        "created_at": _now(),
    }

    with _MEMORY_LOCK:
        thread["turns"].append(turn)
        thread["turns"] = thread["turns"][-MAX_TURNS_PER_THREAD:]
        if scheme:
            thread["last_scheme"] = scheme
        elif use_memory:
            thread["last_scheme"] = thread.get("last_scheme")
        if topic:
            thread["last_topic"] = topic
        elif use_memory:
            thread["last_topic"] = thread.get("last_topic")
        thread["updated_at"] = _now()

    return memory_summary(session_key, thread_key)


def memory_summary(session_id, thread_id="default"):
    _, _, thread = _ensure_thread(session_id, thread_id)
    with _MEMORY_LOCK:
        return {
            "last_scheme": thread.get("last_scheme"),
            "last_topic": thread.get("last_topic"),
            "turn_count": len(thread.get("turns", [])),
        }


def get_thread_history(session_id, thread_id="default"):
    _, _, thread = _ensure_thread(session_id, thread_id)
    with _MEMORY_LOCK:
        return {
            "session_id": session_id,
            "thread_id": _thread_key(thread_id),
            "memory": memory_summary(session_id, thread_id),
            "turns": list(thread.get("turns", [])),
        }
