import re

from mcp_tools.calendar_hold_tool import execute_calendar_hold
from mcp_tools.doc_append_tool import execute_doc_append
from mcp_tools.email_draft_tool import execute_email_draft

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

ACTION_LABELS = {
    "calendar_hold": "Calendar Hold",
    "notes_append": "Notes Entry",
    "email_draft": "Email Draft",
}

TOOL_EXECUTORS = {
    "calendar_hold": execute_calendar_hold,
    "notes_append": execute_doc_append,
    "email_draft": execute_email_draft,
}


def _next_approval_id(actions):
    highest_id = 0
    for action in actions:
        match = re.match(r"APR-(\d+)", action.get("approval_id", ""))
        if match:
            highest_id = max(highest_id, int(match.group(1)))
    return highest_id + 1


def create_pending_actions(actions, booking_code, slot, intent, transcript_summary=""):
    start_id = _next_approval_id(actions)
    action_specs = [
        (
            "calendar_hold",
            f"Calendar Hold for booking {booking_code}, {slot}.",
            {
                "slot": slot,
                "purpose": "Tentative advisor appointment hold",
            },
        ),
        (
            "notes_append",
            f"Notes Entry for booking {booking_code}.",
            {
                "slot": slot,
                "intent": intent,
                "transcript_summary": transcript_summary,
            },
        ),
        (
            "email_draft",
            f"Email Draft for advisor with booking {booking_code}.",
            {
                "slot": slot,
                "intent": intent,
                "auto_send": False,
            },
        ),
    ]

    pending_actions = []
    for index, (action_type, summary, details) in enumerate(action_specs):
        pending_actions.append(
            {
                "approval_id": f"APR-{start_id + index:03d}",
                "type": action_type,
                "action_type": ACTION_LABELS[action_type],
                "status": STATUS_PENDING,
                "summary": summary,
                "details": details,
                "booking_code": booking_code,
                "slot": slot,
                "intent": intent,
                "executed": False,
                "execution_result": None,
            }
        )

    actions.extend(pending_actions)
    return pending_actions


def approve_and_execute_action(action):
    if action["status"] != STATUS_PENDING:
        return action

    action["status"] = STATUS_APPROVED
    executor = TOOL_EXECUTORS.get(action["type"])
    if executor is None:
        action["status"] = STATUS_FAILED
        action["executed"] = False
        action["execution_result"] = "No MCP tool is registered for this action type"
        return action

    try:
        result = executor(action)
        action["status"] = STATUS_COMPLETED
        action["executed"] = True
        action["execution_result"] = result["message"]
        action["tool_result"] = result
    except Exception as error:
        action["status"] = STATUS_FAILED
        action["executed"] = False
        action["execution_result"] = str(error)

    return action


def reject_action(action):
    if action["status"] == STATUS_PENDING:
        action["status"] = STATUS_REJECTED
        action["executed"] = False
        action["execution_result"] = "Rejected by human approver"
    return action
