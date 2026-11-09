from typing import Literal, TypedDict


class TimetableAccessEvent(TypedDict):
    event_id: str
    user_id: str
    course_code: str
    period: int
    day: str
    status: Literal["success", "failure"]
    latency_ms: float
    timestamp: float


class IngestionAuditEvent(TypedDict):
    message_id: int
    chat_id: int
    parsed_intent: str
    validation_result: Literal["pass", "fail"]
    matched_rule: str
    timestamp: float


class AttendanceCheckEvent(TypedDict):
    student_id: str
    course_code: str
    slot_type: Literal["Lecture", "Skill", "Practical"]
    status: Literal["present", "absent", "late"]
    timestamp: float
