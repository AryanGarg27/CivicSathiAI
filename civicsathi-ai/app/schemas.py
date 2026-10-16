from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class CivicRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_type: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=5, max_length=600)
    location: Optional[str] = Field(default=None, max_length=160)
    missing_information: List[str] = Field(default_factory=list, max_length=12)
    suggested_service: str = Field(min_length=2, max_length=160)
    confidence: float = Field(ge=0, le=1)
    needs_human_review: bool = True
