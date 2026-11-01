"""Academic calendar loader, milestone resolution, and Invariant 5 guard support."""

import tomllib
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple


class CalendarEvent(NamedTuple):
    name: str
    start_date: date
    end_date: date
    milestone: str


class AcademicCalendar(NamedTuple):
    terms: dict[str, dict[str, date]]
    events: dict[str, list[CalendarEvent]] | None = None


def load_calendar(path: str | Path | None = None) -> AcademicCalendar | None:
    """Load academic calendar from a TOML file.

    Safely handles missing files, malformed TOML, and unexpected schema structures
    without raising exceptions.
    """
    if path is None:
        try:
            from src.config import settings

            target_path = Path(settings.spark_calendar)
        except Exception:
            target_path = Path("data/calendar_2026_27.toml")
    else:
        target_path = Path(path)

    try:
        with open(target_path, "rb") as f:
            data = tomllib.load(f)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return None
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    terms: dict[str, dict[str, date]] = {}
    events: dict[str, list[CalendarEvent]] = {}

    for term_name, term_data in data.items():
        if not isinstance(term_data, dict):
            continue

        parsed_dates: dict[str, date] = {}
        term_events: list[CalendarEvent] = []

        for k, v in term_data.items():
            if k == "events" and isinstance(v, list):
                for item in v:
                    if not isinstance(item, dict):
                        continue
                    try:
                        ev_name = str(item.get("name", ""))
                        s_date = item.get("start_date")
                        e_date = item.get("end_date", s_date)
                        m_stone = str(item.get("milestone", ""))
                        if isinstance(s_date, str):
                            s_date = date.fromisoformat(s_date)
                        if isinstance(e_date, str):
                            e_date = date.fromisoformat(e_date)
                        if isinstance(s_date, date) and isinstance(e_date, date):
                            term_events.append(
                                CalendarEvent(
                                    name=ev_name,
                                    start_date=s_date,
                                    end_date=e_date,
                                    milestone=m_stone,
                                )
                            )
                    except (ValueError, TypeError):
                        continue
            elif isinstance(v, date):
                parsed_dates[k] = v
            elif isinstance(v, str):
                try:
                    parsed_dates[k] = date.fromisoformat(v)
                except ValueError:
                    pass

        if parsed_dates:
            terms[term_name] = parsed_dates
        if term_events:
            events[term_name] = term_events

    return AcademicCalendar(terms=terms, events=events)


def _normalize_term(term_hint: str) -> str:
    cleaned = term_hint.strip()
    upper = cleaned.upper().replace(" ", "").replace("-", "").replace("_", "")
    if upper in ("T4", "T04", "TRIMESTER4"):
        return "T04"
    if upper in ("T5", "T05", "TRIMESTER5"):
        return "T05"
    if upper in ("T6", "T06", "TRIMESTER6"):
        return "T06"
    if "SUMMER" in upper:
        return "Summer"
    return cleaned


def _resolve_term(
    cal: AcademicCalendar, ref_date: date, term_hint: str | None = None
) -> str | None:
    if not cal.terms:
        return None

    if term_hint:
        norm = _normalize_term(term_hint)
        for t in cal.terms:
            if t.lower() == norm.lower() or t.lower() == term_hint.lower():
                return t

    # Match by term bounds [start, end]
    for term, dates in cal.terms.items():
        all_dates = [v for k, v in dates.items() if not k.endswith("-end")]
        if not all_dates:
            continue
        term_start = dates.get("start") or min(all_dates)
        term_end = dates.get("end") or max(all_dates)
        if term_start <= ref_date <= term_end:
            return term

    # If outside all terms, find nearest following term (or closest term overall)
    best_term: str | None = None
    best_diff: int | None = None

    for term, dates in cal.terms.items():
        all_dates = [v for k, v in dates.items() if not k.endswith("-end")]
        if not all_dates:
            continue
        term_start = dates.get("start") or min(all_dates)
        term_end = dates.get("end") or max(all_dates)

        if ref_date < term_start:
            diff = (term_start - ref_date).days
        elif ref_date > term_end:
            diff = (ref_date - term_end).days + 1000
        else:
            diff = 0

        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_term = term

    return best_term


def _get_window_for_term(
    cal: AcademicCalendar, term: str, milestone: str
) -> tuple[date, date] | None:
    m_clean = milestone.strip().lower()
    variants = [
        m_clean,
        m_clean.replace(" ", "-"),
        m_clean.replace("-", " "),
        m_clean.replace(" examinations", ""),
        m_clean.replace(" exams", ""),
    ]

    events_dict = cal.events or {}
    term_events = events_dict.get(term, [])

    # Exact match on structured events milestone
    for ev in term_events:
        ev_m = ev.milestone.strip().lower()
        if ev_m in variants or ev_m.replace("-", " ") in variants:
            return (ev.start_date, ev.end_date)

    # Exact match on flat dates
    dates = cal.terms.get(term, {})
    for v in variants:
        if v in dates:
            start_d = dates[v]
            end_d = dates.get(f"{v}-end", start_d)
            return (start_d, end_d)

    # Substring / partial match on structured events
    for ev in term_events:
        ev_m = ev.milestone.strip().lower()
        ev_name = ev.name.strip().lower()
        if any(v in ev_m for v in variants if len(v) > 2) or any(
            v in ev_name for v in variants if len(v) > 2
        ):
            return (ev.start_date, ev.end_date)

    return None


def _normalize_args(
    a: Any,
    b: Any,
    c: Any,
) -> tuple[str, date, AcademicCalendar | None]:
    cal: AcademicCalendar | None
    if isinstance(a, AcademicCalendar):
        cal = a
        milestone = str(b)
        raw_date = c
    else:
        milestone = str(a)
        raw_date = b
        cal = c if isinstance(c, AcademicCalendar) else None

    if isinstance(raw_date, str):
        ref_date = date.fromisoformat(raw_date)
    elif isinstance(raw_date, date):
        ref_date = raw_date
    else:
        ref_date = date.today()

    return milestone, ref_date, cal


def get_milestone_date(
    milestone_or_cal: str | AcademicCalendar,
    ref_date_or_milestone: date | str,
    cal_or_ref_date: AcademicCalendar | date | None = None,
    term_hint: str | None = None,
) -> date | None:
    """Find primary milestone date or matching date in valid exam/event window."""
    milestone, ref_date, cal = _normalize_args(
        milestone_or_cal, ref_date_or_milestone, cal_or_ref_date
    )
    if cal is None:
        return None

    term = _resolve_term(cal, ref_date, term_hint)
    if term is None:
        return None

    window = _get_window_for_term(cal, term, milestone)
    if window is not None:
        start_d, end_d = window
        if start_d <= ref_date <= end_d:
            return ref_date
        return start_d

    return None


def get_milestone_window(
    milestone_or_cal: str | AcademicCalendar,
    ref_date_or_milestone: date | str,
    cal_or_ref_date: AcademicCalendar | date | None = None,
    term_hint: str | None = None,
) -> tuple[date, date] | None:
    """Retrieve the official (start_date, end_date) range for a milestone."""
    milestone, ref_date, cal = _normalize_args(
        milestone_or_cal, ref_date_or_milestone, cal_or_ref_date
    )
    if cal is None:
        return None

    term = _resolve_term(cal, ref_date, term_hint)
    if term is None:
        return None

    return _get_window_for_term(cal, term, milestone)
