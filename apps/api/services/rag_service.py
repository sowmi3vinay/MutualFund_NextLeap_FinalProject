from pathlib import Path
import json
import re
from urllib.parse import urlparse

from services.embedding_service import embed_query
from services.faq_memory import detect_scheme, detect_topic
from services.llm_service import INSUFFICIENT_CONTEXT_ANSWER, generate_grounded_answer
from services.vector_store import get_vector_store

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = PROJECT_ROOT / "data" / "sources" / "processed" / "source_chunks.jsonl"
LOW_CONFIDENCE_DISTANCE = 1.35
GENERIC_QUERY_TERMS = {
    "what",
    "which",
    "where",
    "when",
    "does",
    "fund",
    "funds",
    "mutual",
    "scheme",
    "schemes",
    "policy",
    "current",
    "information",
    "question",
    "tell",
    "about",
    "topic",
    "context",
    "current",
    "latest",
    "its",
}


def _query_terms(query):
    return [term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2]


def _rerank_chunks(query, chunks):
    terms = _query_terms(query)
    if not terms:
        return chunks

    query_lower = query.lower()
    phrase_boosts = [
        phrase
        for phrase in [
            "exit load",
            "expense ratio",
            "fee explainer",
            "charged",
            "charges",
            "minimum sip",
            "benchmark",
            "riskometer",
        ]
        if phrase in query_lower
    ]

    def score(chunk):
        distance = chunk.get("distance")
        base_score = 0 if distance is None else -float(distance)
        source_id = (chunk.get("source_id") or "").lower()
        source_type = (chunk.get("source_type") or "").lower()
        title = (chunk.get("title") or "").lower()
        scheme_name = (chunk.get("scheme_name") or "").lower()
        topic = (chunk.get("topic") or "").lower()
        text = (chunk.get("text") or "").lower()

        metadata_score = sum(0.35 for term in terms if term in title or term in scheme_name)
        topic_score = sum(0.15 for term in terms if term in topic)
        text_score = sum(0.03 for term in terms if term in text)
        phrase_score = sum(1.0 for phrase in phrase_boosts if phrase in text or phrase in title)
        exact_exit_load_score = (
            3.0
            if "exit load" in query_lower
            and re.search(r"exit\s+load\s*:?\s*nil", text)
            else 0
        )
        generated_fee_score = (
            2.0
            if source_id.startswith("gen")
            and "review intelligence" in source_type
            and any(term in {"exit", "load", "fee", "fees", "charged", "charges"} for term in terms)
            else 0
        )
        return (
            base_score
            + metadata_score
            + topic_score
            + text_score
            + phrase_score
            + exact_exit_load_score
            + generated_fee_score
        )

    return sorted(chunks, key=score, reverse=True)


def _keyword_chunks(query, limit=10):
    if not CHUNKS_PATH.exists():
        return []

    terms = _query_terms(query)
    query_lower = query.lower()
    phrase_boosts = [
        phrase
        for phrase in [
            "exit load",
            "expense ratio",
            "fee explainer",
            "charged",
            "charges",
            "minimum sip",
            "benchmark",
            "riskometer",
        ]
        if phrase in query_lower
    ]
    scored = []

    with CHUNKS_PATH.open(encoding="utf-8") as chunks_file:
        for line in chunks_file:
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text", "")
            metadata = row.get("metadata", {})
            haystack = " ".join(
                [
                    text,
                    metadata.get("title", ""),
                    metadata.get("scheme_name", ""),
                    metadata.get("topic", ""),
                ]
            ).lower()
            term_score = sum(1 for term in terms if term in haystack)
            phrase_score = sum(5 for phrase in phrase_boosts if phrase in haystack)
            score = term_score + phrase_score
            if score:
                scored.append(
                    (
                        score,
                        {
                            "text": text,
                            "chunk_text": text,
                            "distance": 0.0,
                            "similarity": 1.0,
                            "source_id": metadata.get("source_id"),
                            "url": metadata.get("url"),
                            "title": metadata.get("title"),
                            "source_type": metadata.get("source_type"),
                            "scheme_name": metadata.get("scheme_name"),
                            "topic": metadata.get("topic"),
                        },
                    )
                )

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:limit]]


def _dedupe_chunks(chunks):
    deduped = []
    seen = set()
    for chunk in chunks:
        key = (chunk.get("source_id"), chunk.get("text", "")[:120])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _chunk_matches_scheme(chunk, scheme_name):
    if not scheme_name:
        return True
    haystack = " ".join(
        [
            chunk.get("scheme_name") or "",
            chunk.get("title") or "",
        ]
    ).lower()
    return scheme_name.lower() in haystack


def _chunk_matches_topic(chunk, topic_name):
    if not topic_name:
        return True
    haystack = " ".join(
        [
            chunk.get("topic") or "",
            chunk.get("title") or "",
            chunk.get("text") or "",
        ]
    ).lower()
    return topic_name.lower() in haystack


def retrieve_relevant_chunks(query, top_k=5):
    keyword_only_chunks = _keyword_chunks(query, limit=max(top_k, 10))

    try:
        vector_store = get_vector_store()
        vector_count = vector_store.count()
        if vector_count == 0:
            hybrid_chunks = keyword_only_chunks
        else:
            query_embedding = embed_query(query)
            candidate_count = max(top_k, min(max(top_k * 10, 50), vector_count))
            chunks = vector_store.search(query_embedding, top_k=candidate_count)
            hybrid_chunks = _dedupe_chunks(chunks + keyword_only_chunks)
    except Exception:
        hybrid_chunks = keyword_only_chunks

    reranked_chunks = _rerank_chunks(query, hybrid_chunks)

    detected_scheme = detect_scheme(query)
    detected_topic = detect_topic(query)

    if detected_scheme:
        scheme_chunks = [chunk for chunk in reranked_chunks if _chunk_matches_scheme(chunk, detected_scheme)]
        if scheme_chunks:
            reranked_chunks = scheme_chunks
        else:
            return []

    if detected_topic:
        topic_chunks = [chunk for chunk in reranked_chunks if _chunk_matches_topic(chunk, detected_topic)]
        if topic_chunks:
            reranked_chunks = topic_chunks

    return reranked_chunks[:top_k]


def build_context(chunks):
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"Title: {chunk.get('title') or ''}",
                    f"Source type: {chunk.get('source_type') or ''}",
                    f"Scheme: {chunk.get('scheme_name') or ''}",
                    f"Topic: {chunk.get('topic') or ''}",
                    f"URL: {chunk.get('url') or ''}",
                    "Text:",
                    chunk.get("text") or "",
                ]
            )
        )
    return "\n\n---\n\n".join(context_blocks)


def citations_from_chunks(chunks):
    citations = []
    seen_urls = set()
    for chunk in chunks:
        url = chunk.get("url")
        parsed_url = urlparse(url or "")
        is_external_url = parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)
        citation_key = url if is_external_url else chunk.get("source_id")
        if not citation_key or citation_key in seen_urls:
            continue
        seen_urls.add(citation_key)
        citations.append(
            {
                "title": chunk.get("title") or "Source",
                "url": url if is_external_url else "",
                "is_internal": not is_external_url,
                "source_type": chunk.get("source_type") or "",
                "source_id": chunk.get("source_id") or "",
                "scheme_name": chunk.get("scheme_name") or "",
            }
        )
    return citations


def has_low_retrieval_confidence(chunks):
    if not chunks:
        return True
    if any((chunk.get("similarity") or 0) >= 0.72 for chunk in chunks[:3]):
        return False
    first_distance = chunks[0].get("distance")
    return first_distance is None or first_distance > LOW_CONFIDENCE_DISTANCE


def context_supports_query(question, chunks):
    distinctive_terms = [
        term for term in _query_terms(question) if term not in GENERIC_QUERY_TERMS
    ]
    if not distinctive_terms:
        return True

    context = " ".join(
        [
            chunk.get("text") or ""
            for chunk in chunks
        ]
        + [
            chunk.get("title") or ""
            for chunk in chunks
        ]
        + [
            chunk.get("scheme_name") or ""
            for chunk in chunks
        ]
    ).lower()
    matched_terms = [term for term in distinctive_terms if term in context]
    return len(matched_terms) / len(distinctive_terms) >= 0.6


def answer_question_from_corpus(question, top_k=5):
    chunks = retrieve_relevant_chunks(question, top_k=top_k)
    citations = citations_from_chunks(chunks)

    if has_low_retrieval_confidence(chunks) or not context_supports_query(question, chunks):
        return {
            "answer": INSUFFICIENT_CONTEXT_ANSWER,
            "citations": [],
            "source_badge": "No Source Found",
            "needs_clarification": False,
            "retrieved_chunks": chunks,
        }

    context = build_context(chunks)
    answer = generate_grounded_answer(question, context)
    return {
        "answer": answer,
        "citations": citations,
        "source_badge": "Official Source" if citations else "No Source Found",
        "needs_clarification": False,
        "retrieved_chunks": chunks,
    }


def retrieve_facts(question):
    return {
        "question": question,
        "chunks": retrieve_relevant_chunks(question),
        "message": "Retrieval-only response. Final answer generation is not implemented yet.",
    }
