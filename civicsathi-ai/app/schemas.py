from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

Category = Literal['grievance', 'property_tax', 'echallan', 'horticulture', 'license', 'water_sewage', 'other']
Status = Literal['received', 'under_review', 'in_progress', 'resolved', 'rejected']


class StrictModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class IntakeRequest(StrictModel):
    text: str = Field(default='', max_length=3000)
    photo_id: UUID | None = None


class Draft(StrictModel):
    category: Category = 'other'
    summary: str = Field(min_length=1, max_length=500)
    location: str | None = Field(default=None, max_length=250)
    missing_fields: list[str] = Field(default_factory=list, max_length=12)
    language: str = Field(default='unknown', max_length=40)
    confidence: float = Field(default=0.0, ge=0, le=1)
    photo_id: UUID | None = None


class PhotoAnalysis(StrictModel):
    description: str = Field(min_length=1, max_length=500)
    category: Literal['grievance', 'horticulture', 'water_sewage', 'other']
    visible_evidence: list[str] = Field(max_length=8)
    uncertainty: str = Field(default='', max_length=500)
    needs_clarification: bool = True
    follow_up_question: str = Field(default='', max_length=250)


class PhotoRequest(StrictModel):
    image_base64: str = Field(min_length=20, max_length=3_400_000)
    mime_type: Literal['image/jpeg', 'image/png', 'image/webp'] = 'image/jpeg'
    text: str = Field(default='', max_length=3000)


class SubmitRequest(StrictModel):
    draft: Draft
    confirmed: bool
    request_id: UUID


class UpdateRequest(StrictModel):
    status: Status
    note: str = Field(default='', max_length=500)


class RegisterRequest(StrictModel):
    email: str = Field(min_length=5, max_length=254)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(StrictModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ServiceRequest(StrictModel):
    service_type: Literal['health_appointment', 'senior_card', 'disability_card', 'old_age_pension', 'widow_pension', 'disability_pension', 'horticulture']
    applicant_name: str = Field(min_length=2, max_length=100)
    contact_phone: str = Field(min_length=8, max_length=20)
    details: dict[str, str] = Field(default_factory=dict, max_length=12)
