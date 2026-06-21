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


def generate_grounded_answer(question, context):
    if not context.strip():
        return INSUFFICIENT_CONTEXT_ANSWER

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
        return INSUFFICIENT_CONTEXT_ANSWER
    return limit_to_three_sentences(answer)


def generate_extractive_answer(question, context):
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
