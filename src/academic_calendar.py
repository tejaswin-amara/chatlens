import tomllib
from datetime import date
from typing import NamedTuple


class AcademicCalendar(NamedTuple):
    terms: dict[str, dict[str, date]]


def load_calendar(path: str = "data/calendar_2026_27.toml") -> AcademicCalendar | None:
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return None

    terms = {}
    for term_name, term_data in data.items():
        parsed_dates = {}
        for k, v in term_data.items():
            if isinstance(v, date):
                parsed_dates[k] = v
        if parsed_dates:
            terms[term_name] = parsed_dates

    return AcademicCalendar(terms=terms)


def get_milestone_date(milestone: str, ref_date: date, cal: AcademicCalendar) -> date | None:
    # find the term whose window contains the message date
    # (nearest following term when between terms)
    best_term = None
    best_diff = None

    for term, dates in cal.terms.items():
        # Need to know the term bounds. Assuming start/end or we just use the first/last date.
        all_dates = list(dates.values())
        if not all_dates:
            continue
        term_start = min(all_dates)
        term_end = max(all_dates)

        if term_start <= ref_date <= term_end:
            best_term = term
            break

        if ref_date < term_start:
            diff = (term_start - ref_date).days
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_term = term

    if best_term and milestone in cal.terms[best_term]:
        return cal.terms[best_term][milestone]

    return None
