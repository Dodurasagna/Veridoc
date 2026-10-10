from datetime import date
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobCreate(BaseModel):
    course_name: str = Field(min_length=1, max_length=200)
    organization: str = Field(min_length=1, max_length=200)
    issue_date: date
    recipients: list[Any] = Field(min_length=1, max_length=500)

    @field_validator("course_name", "organization")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class RecipientInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("email must be a valid email address")
        return value


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    total_submitted: int
    valid_count: int
    invalid_count: int
    validation_errors: list[dict]

