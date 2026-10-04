"""Pydantic models for extracted academic events and action items."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedAcademicEvent(BaseModel):
    intent: Literal[
        "ROOM_OVERRIDE", "HOLIDAY", "EXAM_DEADLINE",
        "TASK", "CLASS_CANCELLED", "UNKNOWN"
    ] = Field(
        description="The primary intent of the message or notice."
    )
    course_name: str | None = Field(
        default=None,
        description="Identified course name (e.g. DSA, OSSP, ML, ESD, DBSE, Japanese)",
    )
    course_code: str | None = Field(
        default=None, description="Course code if present (e.g., 25CS2103E)"
    )
    room: str | None = Field(
        default=None,
        description="Updated room number (e.g., H-005, HC-15C, H-301A, H107A, H006)",
    )
    target_date: str | None = Field(
        default=None, description="Target date in ISO YYYY-MM-DD format"
    )
    period: str | None = Field(
        default=None,
        description="Period specification (e.g., P3-P4, Period 1, 10:00 AM - 11:40 AM)",
    )
    summary: str = Field(description="A concise summary of the notice, change, or task")
    action_required: bool = Field(
        default=False, description="True if a specific user task/action is required"
    )
