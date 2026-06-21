def execute_calendar_hold(action):
    return {
        "tool": "calendar_hold",
        "message": "Tentative advisor hold created",
        "booking_code": action.get("booking_code"),
        "slot": action.get("slot"),
        "executed": True,
    }
