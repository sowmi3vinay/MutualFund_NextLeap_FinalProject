from fastapi import APIRouter

from services.mcp_orchestrator import approve_and_execute_action, reject_action as reject_pending_action

router = APIRouter()

_ACTIONS = []


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
