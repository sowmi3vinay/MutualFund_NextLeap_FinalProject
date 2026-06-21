def execute_doc_append(action):
    return {
        "tool": "doc_append",
        "message": "Notes updated",
        "booking_code": action.get("booking_code"),
        "details": action.get("details", {}),
        "executed": True,
    }
