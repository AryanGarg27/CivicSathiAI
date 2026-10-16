import pytest
from app.permissions import authorize_tool, PermissionDenied

def test_real_complaint_submission_denied_by_default():
    with pytest.raises(PermissionDenied):
        authorize_tool("submit_real_complaint")

def test_non_consequential_action_allowed():
    authorize_tool("show_service_guidance")
