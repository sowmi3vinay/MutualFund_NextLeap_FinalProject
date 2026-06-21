def execute_email_draft(action):
    return {
        "tool": "email_draft",
        "message": "Advisor draft created",
        "booking_code": action.get("booking_code"),
        "auto_sent": False,
        "executed": True,
    }
