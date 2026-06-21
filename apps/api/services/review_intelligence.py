import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.refresh_vector_store import refresh_vector_store  # noqa: E402

REVIEWS_PATH = PROJECT_ROOT / "data" / "reviews" / "sample_reviews.csv"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"
WEEKLY_PULSE_PATH = OUTPUTS_DIR / "weekly_pulse.json"
FEE_EXPLAINER_PATH = OUTPUTS_DIR / "fee_explainer.md"
MANIFEST_PATH = PROJECT_ROOT / "data" / "sources" / "source_manifest.csv"
CHUNKS_PATH = PROJECT_ROOT / "data" / "sources" / "processed" / "source_chunks.jsonl"

FEE_SOURCE_ID = "GEN001"
FEE_SOURCE_TITLE = "Review-Derived Fee Explainer"
FEE_SOURCE_URL = "data/outputs/fee_explainer.md"

OFFICIAL_FEE_LINKS = [
    "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=expenseRatio",
    "https://investor.sebi.gov.in/Investor-charter.html",
]

THEME_KEYWORDS = {
    "Exit Load Confusion": [
        "exit load",
        "redemption charge",
        "redemption charges",
        "redeemed",
        "redemption",
        "sold",
    ],
    "SIP Mandate Issues": [
        "sip",
        "mandate",
        "auto-debit",
        "registration",
        "rejected",
        "failed",
    ],
    "Capital Gains Statement Access": [
        "capital gains",
        "tax",
        "statement",
        "statements",
        "documents",
        "report",
    ],
    "Expense Ratio / Fee Clarity": [
        "expense ratio",
        "expenses",
        "fee",
        "fees",
        "charges",
        "breakdown",
    ],
    "App Navigation": [
        "navigation",
        "menus",
        "dashboard",
        "search",
        "access",
        "finding",
        "locate",
        "hidden",
    ],
}

FEE_TOPIC_KEYWORDS = {
    "Exit Load": THEME_KEYWORDS["Exit Load Confusion"],
    "Expense Ratio": THEME_KEYWORDS["Expense Ratio / Fee Clarity"],
}


@dataclass
class Review:
    review_id: str
    date: str
    channel: str
    rating: int
    review_text: str


def _repo_path(path):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _redact_pii(text):
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[redacted]", text)
    text = re.sub(r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b", "[redacted]", text)
    text = re.sub(r"\b\d{9,18}\b", "[redacted]", text)
    return text


def load_reviews(csv_path=REVIEWS_PATH):
    path = _repo_path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Missing reviews CSV: {path}")

    reviews = []
    with path.open(newline="", encoding="utf-8") as reviews_file:
        reader = csv.DictReader(reviews_file)
        for row in reader:
            review_id = (row.get("review_id") or "").strip()
            review_text = _clean_text(row.get("review_text"))
            if not review_id or review_id == "review_id" or not review_text:
                continue
            try:
                rating = int(row.get("rating") or 0)
            except ValueError:
                rating = 0
            reviews.append(
                Review(
                    review_id=review_id,
                    date=(row.get("date") or "").strip(),
                    channel=(row.get("channel") or "").strip(),
                    rating=rating,
                    review_text=_redact_pii(review_text),
                )
            )
    return reviews


def _keyword_hits(text, keywords):
    text_lower = text.lower()
    return sum(1 for keyword in keywords if keyword in text_lower)


def detect_recurring_themes(reviews):
    theme_counts = Counter({theme: 0 for theme in THEME_KEYWORDS})
    theme_scores = Counter({theme: 0 for theme in THEME_KEYWORDS})
    theme_review_ids = {theme: [] for theme in THEME_KEYWORDS}

    for review in reviews:
        for theme, keywords in THEME_KEYWORDS.items():
            hits = _keyword_hits(review.review_text, keywords)
            if hits:
                theme_counts[theme] += 1
                theme_scores[theme] += hits
                theme_review_ids[theme].append(review.review_id)

    return [
        {
            "theme": theme,
            "count": theme_counts[theme],
            "keyword_score": theme_scores[theme],
            "review_ids": theme_review_ids[theme],
        }
        for theme in THEME_KEYWORDS
    ]


def rank_themes(themes):
    return sorted(
        themes,
        key=lambda theme: (
            -theme["count"],
            -theme["keyword_score"],
            list(THEME_KEYWORDS).index(theme["theme"]),
        ),
    )


def extract_representative_quotes(reviews, theme, limit=3):
    keywords = THEME_KEYWORDS.get(theme, [])
    candidates = []
    for review in reviews:
        hits = _keyword_hits(review.review_text, keywords)
        if hits:
            quote = review.review_text.strip()
            if len(quote) > 140:
                quote = quote[:137].rstrip() + "..."
            candidates.append((hits, review.rating, review.review_id, quote))

    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [quote for _, _, _, quote in candidates[:limit]]


def identify_top_theme(themes):
    ranked = rank_themes(themes)
    return ranked[0] if ranked else {"theme": "No Dominant Theme", "count": 0, "keyword_score": 0}


def _most_confused_fee_topic(reviews):
    topic_counts = Counter()
    for review in reviews:
        for topic, keywords in FEE_TOPIC_KEYWORDS.items():
            if _keyword_hits(review.review_text, keywords):
                topic_counts[topic] += 1
    if not topic_counts:
        return "Expense Ratio"
    return topic_counts.most_common(1)[0][0]


def _action_ideas(top_theme):
    action_map = {
        "Exit Load Confusion": [
            "Show exit-load rules before redemption confirmation.",
            "Add a short exit-load example beside the redemption form.",
            "Create an advisor briefing tag for exit-load questions.",
        ],
        "SIP Mandate Issues": [
            "Clarify mandate status messages after SIP setup.",
            "Add next-step guidance for failed auto-debits.",
            "Create an advisor briefing tag for SIP mandate issues.",
        ],
        "Capital Gains Statement Access": [
            "Surface capital-gains statements from the main documents area.",
            "Add search synonyms for tax and capital-gains documents.",
            "Create an advisor briefing tag for statement-access questions.",
        ],
        "Expense Ratio / Fee Clarity": [
            "Add a plain-language expense-ratio note near fund details.",
            "Separate recurring fund expenses from one-time charges.",
            "Create an advisor briefing tag for fee-clarity questions.",
        ],
        "App Navigation": [
            "Reduce menu depth for common support documents.",
            "Improve search labels for statements and fee information.",
            "Create an advisor briefing tag for navigation complaints.",
        ],
    }
    return action_map.get(
        top_theme,
        [
            "Review unclear support labels.",
            "Improve help text near high-friction journeys.",
            "Create an advisor briefing tag for recurring confusion.",
        ],
    )


def generate_weekly_product_pulse(reviews, themes):
    ranked_themes = rank_themes(themes)
    top_theme = identify_top_theme(themes)
    top_theme_name = top_theme["theme"]
    quotes = extract_representative_quotes(reviews, top_theme_name, limit=2)
    if not quotes and reviews:
        quotes = [reviews[0].review_text]
    actions = _action_ideas(top_theme_name)
    top_theme_names = [theme["theme"] for theme in ranked_themes if theme["count"] > 0][:5]
    theme_counts = {theme["theme"]: theme["count"] for theme in ranked_themes}
    key_observation = (
        f"{top_theme_name} is the leading theme with {top_theme['count']} matching reviews."
    )

    weekly_pulse = (
        f"Top themes: {', '.join(top_theme_names)}.\n"
        f"Theme counts: {theme_counts}.\n"
        f"Representative quote: \"{quotes[0] if quotes else 'No quote available.'}\"\n"
        f"Key observation: {key_observation}\n"
        f"Action ideas: 1. {actions[0]} 2. {actions[1]} 3. {actions[2]}"
    )
    words = weekly_pulse.split()
    if len(words) > 250:
        weekly_pulse = " ".join(words[:250])

    return {
        "top_theme": top_theme_name,
        "top_themes": top_theme_names,
        "theme_counts": theme_counts,
        "representative_quotes": quotes,
        "key_observation": key_observation,
        "actions": actions,
        "weekly_pulse": weekly_pulse,
    }


def generate_fee_explainer(reviews):
    topic = _most_confused_fee_topic(reviews)
    if topic == "Exit Load":
        bullets = [
            "Exit load is a charge that may apply when units are redeemed within a stated period.",
            "The rule can differ by scheme, so the latest KIM or SID should be checked before redemption.",
            "Each purchase or SIP instalment can have its own holding period, so dates matter.",
            "The charge is usually calculated on the redemption value of the units covered by the rule.",
            "Exit load is separate from regular scheme expenses such as the expense ratio.",
            "This is general information and does not recommend whether to redeem or hold a fund.",
        ]
    else:
        bullets = [
            "Expense ratio is the recurring cost charged by a mutual fund scheme for managing and operating it.",
            "It is reflected in the scheme's net asset value rather than usually being paid as a separate bill.",
            "Direct and regular plans can have different expense ratios for the same scheme.",
            "A lower expense ratio does not by itself make a scheme suitable for an investor.",
            "Investors should compare the latest disclosed expense ratio in official scheme documents.",
            "This is general information and does not recommend any fund or plan.",
        ]

    lines = [f"# Fee Explainer: {topic}", ""]
    lines.extend([f"- {bullet}" for bullet in bullets])
    lines.extend(
        [
            "",
            "Official sources:",
            f"1. {OFFICIAL_FEE_LINKS[0]}",
            f"2. {OFFICIAL_FEE_LINKS[1]}",
            "",
            f"Last checked: {date.today().isoformat()}",
        ]
    )
    return topic, "\n".join(lines) + "\n"


def _write_weekly_pulse(payload):
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    WEEKLY_PULSE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_fee_explainer(markdown):
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    FEE_EXPLAINER_PATH.write_text(markdown, encoding="utf-8")


def _read_manifest_rows():
    if not MANIFEST_PATH.exists():
        return [], []
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as manifest_file:
        reader = csv.DictReader(manifest_file)
        return reader.fieldnames or [], list(reader)


def _upsert_fee_explainer_source(fee_topic):
    fieldnames, rows = _read_manifest_rows()
    if not fieldnames:
        fieldnames = [
            "source_id",
            "url",
            "title",
            "source_type",
            "scheme_name",
            "topic",
            "date_checked",
            "is_official",
        ]

    rows = [row for row in rows if row.get("source_id") != FEE_SOURCE_ID]
    rows.append(
        {
            "source_id": FEE_SOURCE_ID,
            "url": FEE_SOURCE_URL,
            "title": FEE_SOURCE_TITLE,
            "source_type": "Generated Review Intelligence",
            "scheme_name": "HDFC schemes",
            "topic": fee_topic,
            "date_checked": date.today().isoformat(),
            "is_official": "false",
        }
    )

    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(manifest_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _upsert_fee_explainer_chunk(fee_topic, markdown):
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    if CHUNKS_PATH.exists():
        with CHUNKS_PATH.open(encoding="utf-8") as chunks_file:
            for line in chunks_file:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("metadata", {}).get("source_id") != FEE_SOURCE_ID:
                    chunks.append(chunk)

    chunks.append(
        {
            "id": f"{FEE_SOURCE_ID}-CHUNK-0001",
            "text": markdown,
            "metadata": {
                "source_id": FEE_SOURCE_ID,
                "url": FEE_SOURCE_URL,
                "title": FEE_SOURCE_TITLE,
                "source_type": "Generated Review Intelligence",
                "scheme_name": "HDFC schemes",
                "topic": fee_topic,
            },
        }
    )

    with CHUNKS_PATH.open("w", encoding="utf-8") as chunks_file:
        for chunk in chunks:
            chunks_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def refresh_fee_explainer_feedback_loop(fee_topic, markdown):
    _upsert_fee_explainer_source(fee_topic)
    _upsert_fee_explainer_chunk(fee_topic, markdown)
    refresh_vector_store()


def generate_review_intelligence(reviews_csv_path=REVIEWS_PATH, refresh_vectors=True):
    reviews = load_reviews(reviews_csv_path)
    themes = detect_recurring_themes(reviews)
    pulse = generate_weekly_product_pulse(reviews, themes)
    fee_topic, fee_explainer = generate_fee_explainer(reviews)

    weekly_payload = {
        "generated_at": date.today().isoformat(),
        "review_count": len(reviews),
        "top_theme": pulse["top_theme"],
        "top_themes": pulse["top_themes"],
        "theme_counts": pulse["theme_counts"],
        "representative_quotes": pulse["representative_quotes"],
        "key_observation": pulse["key_observation"],
        "actions": pulse["actions"],
        "weekly_pulse": pulse["weekly_pulse"],
        "fee_topic": fee_topic,
    }
    _write_weekly_pulse(weekly_payload)
    _write_fee_explainer(fee_explainer)
    if refresh_vectors:
        refresh_fee_explainer_feedback_loop(fee_topic, fee_explainer)

    return {
        "top_theme": pulse["top_theme"],
        "weekly_pulse": pulse["weekly_pulse"],
        "fee_explainer": fee_explainer,
        "actions": pulse["actions"],
    }
