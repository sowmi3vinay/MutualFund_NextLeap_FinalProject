ADVICE_REFUSAL = (
    "I cannot provide investment advice, recommend funds, predict returns, or suggest portfolio "
    "allocation. I can explain factual mutual fund information from official sources, or you can "
    "refer to AMFI investor education material."
)

AMFI_INVESTOR_EDUCATION_CITATION = {
    "title": "AMFI Investor Education",
    "url": "https://www.amfiindia.com/investor-corner/knowledge-center",
    "source_type": "AMFI",
}


def contains_pii(text):
    pii_markers = ["pan", "folio", "email", "phone", "bank account"]
    return any(marker in text.lower() for marker in pii_markers)


def is_advice_request(text):
    lowered = text.lower()
    advice_markers = [
        "which fund should i invest",
        "should i invest",
        "best fund",
        "best mf",
        "best mutual fund",
        "which is best mf",
        "which is the best mf",
        "which is best mutual fund",
        "recommend a fund",
        "recommend fund",
        "which fund is best",
        "highest return",
        "highest returns",
        "future return",
        "return prediction",
        "predict returns",
        "portfolio allocation",
        "allocate my portfolio",
        "how much should i invest",
        "where should i invest",
        "rank funds",
        "top performing fund",
        "best performing fund",
    ]
    return any(marker in lowered for marker in advice_markers)


def advice_refusal_response():
    return {
        "answer": ADVICE_REFUSAL,
        "citations": [AMFI_INVESTOR_EDUCATION_CITATION],
        "source_badge": "Investor Education",
        "needs_clarification": False,
    }
