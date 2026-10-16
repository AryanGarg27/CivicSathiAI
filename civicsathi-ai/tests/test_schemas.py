import pytest
from pydantic import ValidationError
from app.schemas import CivicRequest

def test_valid_request_schema():
    value = CivicRequest(request_type="complaint", category="Waste", summary="Garbage is piling up near the park.", location="Sector 22", missing_information=[], suggested_service="Waste complaint guidance", confidence=0.6, needs_human_review=True)
    assert value.needs_human_review is True

def test_confidence_range_enforced():
    with pytest.raises(ValidationError):
        CivicRequest(request_type="complaint", category="Waste", summary="Garbage piling up near park.", suggested_service="Guidance", confidence=1.5)
