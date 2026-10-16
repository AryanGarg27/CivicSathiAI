class PermissionDenied(PermissionError):
    pass

FORBIDDEN_TOOL_ACTIONS = {
    "submit_real_complaint", "approve_application", "enforce_regulation",
    "close_case", "issue_penalty", "access_private_municipal_records",
}

def authorize_tool(action: str, *, explicitly_authorized: bool = False) -> None:
    """Deny consequential/live actions by default in this independent prototype."""
    if action in FORBIDDEN_TOOL_ACTIONS and not explicitly_authorized:
        raise PermissionDenied(f"Action '{action}' is not enabled in this prototype")
