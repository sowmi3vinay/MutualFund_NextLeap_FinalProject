from fastapi import APIRouter

from services.mcp_orchestrator import approve_and_execute_action, reject_action as reject_pending_action

router = APIRouter()

_ACTIONS = [
    {
        "approval_id": "APR-001",
        "type": "calendar_hold",
        "action_type": "Calendar Hold",
        "status": "pending",
        "summary": "Mock calendar hold for booking KV-B391, Friday 3:00 PM.",
        "details": {"slot": "Friday 3:00 PM", "purpose": "Tentative advisor appointment hold"},
        "booking_code": "KV-B391",
        "executed": False,
        "execution_result": None,
    },
    {
        "approval_id": "APR-002",
        "type": "notes_append",
        "action_type": "Notes Entry",
        "status": "pending",
        "summary": "Append booking notes for SIP mandate discussion.",
        "details": {"intent": "book_appointment", "transcript_summary": "SIP mandate discussion"},
        "booking_code": "KV-B391",
        "executed": False,
        "execution_result": None,
    },
    {
        "approval_id": "APR-003",
        "type": "email_draft",
        "action_type": "Email Draft",
        "status": "pending",
        "summary": "Draft advisor email with booking context.",
        "details": {"intent": "book_appointment", "auto_send": False},
        "booking_code": "KV-B391",
        "executed": False,
        "execution_result": None,
    },
]


def _find_action(approval_id):
    return next((action for action in _ACTIONS if action["approval_id"] == approval_id), None)


@router.get("/pending")
def pending_approvals():
    return {"actions": _ACTIONS}


@router.post("/{approval_id}/approve")
def approve_action(approval_id: str):
    action = _find_action(approval_id)
    if action is None:
        return {"approval_id": approval_id, "status": "not_found", "executed": False}

    return approve_and_execute_action(action)


@router.post("/{approval_id}/reject")
def reject_action(approval_id: str):
    action = _find_action(approval_id)
    if action is None:
        return {"approval_id": approval_id, "status": "not_found", "executed": False}

    return reject_pending_action(action)
