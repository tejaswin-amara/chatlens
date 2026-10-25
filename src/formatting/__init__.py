"""Message formatting and design system package for ChatLens PA."""

from src.formatting.templates import (
    get_standard_navigation_buttons,
    render_attendance_card,
    render_day_schedule,
    render_deadlines_card,
    render_proactive_reminder,
    render_status_card,
)

__all__ = [
    "get_standard_navigation_buttons",
    "render_attendance_card",
    "render_day_schedule",
    "render_deadlines_card",
    "render_proactive_reminder",
    "render_status_card",
]
