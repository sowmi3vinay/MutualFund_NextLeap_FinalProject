from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Query

from services.compliance_guardrails import advice_refusal_response, is_advice_request
from services.faq_memory import contextualize_question, get_thread_history, remember_turn
from services.rag_service import answer_question_from_corpus, retrieve_relevant_chunks

router = APIRouter()


class FAQRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    thread_id: Optional[str] = "default"


@router.post("/ask")
def ask_faq(request: FAQRequest):
    if is_advice_request(request.question):
        memory_context = contextualize_question(
            request.question,
            session_id=request.session_id,
            thread_id=request.thread_id,
        )
        response = advice_refusal_response()
        memory = remember_turn(
            memory_context["session_id"],
            memory_context["thread_id"],
            request.question,
            response["answer"],
            response.get("citations", []),
        )
        response.update(
            {
                "session_id": memory_context["session_id"],
                "thread_id": memory_context["thread_id"],
                "rewritten_question": memory_context["rewritten_question"],
                "memory": memory,
            }
        )
        return response

    memory_context = contextualize_question(
        request.question,
        session_id=request.session_id,
        thread_id=request.thread_id,
    )
    response = answer_question_from_corpus(memory_context["rewritten_question"], top_k=5)
    response.pop("retrieved_chunks", None)
    memory = remember_turn(
        memory_context["session_id"],
        memory_context["thread_id"],
        memory_context["rewritten_question"],
        response["answer"],
        response.get("citations", []),
    )
    response.update(
        {
            "session_id": memory_context["session_id"],
            "thread_id": memory_context["thread_id"],
            "rewritten_question": memory_context["rewritten_question"],
            "memory": memory,
        }
    )
    return response


@router.get("/retrieve-test")
def retrieve_test(query: str = Query(..., min_length=1), top_k: int = 5):
    return {
        "query": query,
        "top_k": top_k,
        "results": retrieve_relevant_chunks(query, top_k=top_k),
    }


@router.get("/memory/{session_id}")
def faq_memory(session_id: str, thread_id: str = Query("default")):
    return get_thread_history(session_id, thread_id=thread_id)
