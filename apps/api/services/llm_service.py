import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

GROQ_MODEL = "llama-3.3-70b-versatile"
INSUFFICIENT_CONTEXT_ANSWER = (
    "The current corpus does not contain enough information to answer this question."
)


def _load_environment():
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")


def get_groq_client():
    _load_environment()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def limit_to_three_sentences(text):
    text = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentence for sentence in sentences[:3] if sentence).strip()


def _extract_structured_answer(question, context):
    lowered_question = question.lower()
    flattened_context = " ".join(context.split())

    if "exit load" in lowered_question:
        nil_match = re.search(
            r"(?:exit\s+load[^.:\n]{0,80}[:\-]?\s*)(nil|none|not\s+applicable|no\s+exit\s+load)",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if nil_match:
            return "The exit load is Nil."

        percent_match = re.search(
            r"exit\s+load[^.:\n]{0,120}?(?:of\s+)?(\d+(?:\.\d+)?)%\s+is\s+payable\s+if\s+units?\s+are\s+redeemed/?\s*switched-out\s+within\s+([^.]*)",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if percent_match:
            percent = percent_match.group(1)
            condition = percent_match.group(2).strip(" .;,:")
            condition = re.sub(r"\s+", " ", condition)
            return f"The exit load is {percent}% if units are redeemed or switched out within {condition}."

        load_structure_match = re.search(
            r"load\s+structure\s+exit\s+load[:\-]?\s*(.*?)\s*(?:no\s+entry\s+load|$)",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if load_structure_match:
            clause = re.sub(r"\s+", " ", load_structure_match.group(1)).strip(" .;,:")
            if clause:
                return f"The exit load is {clause}."

    if "riskometer" in lowered_question or re.search(r"\brisk\b", lowered_question):
        for risk_level in [
            "very high",
            "moderately high",
            "low to moderate",
            "moderate",
            "low",
        ]:
            if risk_level in flattened_context.lower():
                return f"The scheme riskometer for this fund is {risk_level.title()}."

        if "for latest riskometer" in flattened_context.lower():
            return INSUFFICIENT_CONTEXT_ANSWER

    if "benchmark" in lowered_question:
        benchmark_match = re.search(
            r"(nifty\s+[a-z0-9\s&/-]+?index\s*\(tri\))",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if benchmark_match:
            benchmark = re.sub(r"\s+", " ", benchmark_match.group(1)).strip()
            return f"The benchmark is {benchmark}."

        benchmark_match = re.search(
            r"benchmark[^.:\n]{0,80}[:\-]?\s*(nifty\s+[a-z0-9\s&/-]+)",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if benchmark_match:
            benchmark = re.sub(r"\s+", " ", benchmark_match.group(1)).strip(" .;,:")
            return f"The benchmark is {benchmark}."

    if "expense ratio" in lowered_question or lowered_question.startswith("what is the ter"):
        regular_match = re.search(
            r"regular\s+plan\s*:\s*(\d+(?:\.\d+)?)%\s*p\.a\.",
            flattened_context,
            flags=re.IGNORECASE,
        )
        direct_match = re.search(
            r"direct\s+plan\s*:\s*(\d+(?:\.\d+)?)%\s*p\.a\.",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if regular_match and direct_match:
            return (
                "The retrieved documents list actual expenses for the previous financial year ended "
                f"March 31, 2025 as Regular Plan: {regular_match.group(1)}% p.a. and Direct Plan: {direct_match.group(1)}% p.a."
            )

        if "total expense ratio" in flattened_context.lower() or "ter" in flattened_context.lower():
            return (
                "The retrieved documents point to the AMC TER disclosure page for the current expense ratio, "
                "but do not provide a single current TER figure in the retrieved text."
            )

    return None


def generate_grounded_answer(question, context):
    if not context.strip():
        return INSUFFICIENT_CONTEXT_ANSWER

    structured_answer = _extract_structured_answer(question, context)
    if structured_answer:
        return structured_answer

    client = get_groq_client()
    if client is None:
        return generate_extractive_answer(question, context)

    system_prompt = (
        "You are a facts-only mutual fund support assistant. Answer only using the provided "
        "context. Do not provide investment advice, fund recommendations, return predictions, "
        "or portfolio allocation advice. Keep the answer to three sentences or fewer. If the "
        f"context does not contain the answer, say exactly: {INSUFFICIENT_CONTEXT_ANSWER}"
    )
    user_prompt = f"Question:\n{question}\n\nContext:\n{context}"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=220,
        )
    except Exception:
        return generate_extractive_answer(question, context)

    answer = response.choices[0].message.content.strip()
    if not answer:
        return INSUFFICIENT_CONTEXT_ANSWER
    if INSUFFICIENT_CONTEXT_ANSWER.lower() in answer.lower():
        extractive_answer = generate_extractive_answer(question, context)
        if extractive_answer != INSUFFICIENT_CONTEXT_ANSWER:
            return extractive_answer
        return INSUFFICIENT_CONTEXT_ANSWER
    return limit_to_three_sentences(answer)


def generate_extractive_answer(question, context):
    structured_answer = _extract_structured_answer(question, context)
    if structured_answer:
        return structured_answer

    lowered_question = question.lower()
    flattened_context = " ".join(context.split())

    if "riskometer" in lowered_question or re.search(r"\brisk\b", lowered_question):
        for risk_level in [
            "very high",
            "moderately high",
            "low to moderate",
            "moderate",
            "low",
        ]:
            if risk_level in flattened_context.lower():
                return f"The scheme riskometer for this fund is {risk_level.title()}."
        risk_match = re.search(
            r"(?:scheme\s+riskometer[#:\s-]*|riskometer[#:\s-]*)(very high|moderately high|moderate|low to moderate|low)",
            flattened_context,
            flags=re.IGNORECASE,
        )
        if risk_match:
            risk_level = risk_match.group(1).title()
            return f"The scheme riskometer for this fund is {risk_level}."
        return INSUFFICIENT_CONTEXT_ANSWER

    query_terms = {
        term
        for term in re.findall(r"[a-z0-9]+", question.lower())
        if len(term) > 2 and term not in {"what", "which", "where", "when", "how", "does", "for"}
    }
    chunk_texts = []
    for block in context.split("---"):
        if "Text:" in block:
            chunk_texts.append(block.split("Text:", 1)[1])
    source_text = " ".join(chunk_texts) if chunk_texts else context
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(source_text.split()))
    scored_sentences = []

    for sentence in sentences:
        lowered_sentence = sentence.lower()
        score = sum(1 for term in query_terms if term in lowered_sentence)
        if "exit load" in question.lower() and "exit load" in lowered_sentence:
            score += 4
        if score:
            scored_sentences.append((score, sentence.strip()))

    if not scored_sentences:
        return INSUFFICIENT_CONTEXT_ANSWER

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    selected = []
    seen = set()
    for _, sentence in scored_sentences:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append(sentence)
        if len(selected) == 3:
            break

    answer = limit_to_three_sentences(" ".join(selected))
    return answer or INSUFFICIENT_CONTEXT_ANSWER
