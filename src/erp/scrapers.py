"""ERP HTML scrapers and data parsers using Python standard library html.parser."""

import math
import re
from html.parser import HTMLParser
from typing import Any


class HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "table":
            self._current_table = []
        elif tag.lower() == "tr":
            self._current_row = []
        elif tag.lower() in ("td", "th"):
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("td", "th"):
            self._in_cell = False
            cell_text = "".join(self._current_cell).strip()
            cell_text = re.sub(r"\s+", " ", cell_text)
            self._current_row.append(cell_text)
        elif tag.lower() == "tr":
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = []
        elif tag.lower() == "table":
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)


def parse_generic_tables(html: str) -> list[list[dict[str, str]]]:
    """Parses all HTML tables into lists of dictionaries keyed by header row."""
    parser = HTMLTableParser()
    parser.feed(html)
    result: list[list[dict[str, str]]] = []

    for tbl in parser.tables:
        if len(tbl) < 2:
            continue
        headers = [h.strip() for h in tbl[0]]
        rows: list[dict[str, str]] = []
        for row in tbl[1:]:
            row_dict: dict[str, str] = {}
            for i, header in enumerate(headers):
                val = row[i].strip() if i < len(row) else ""
                row_dict[header] = val
            rows.append(row_dict)
        if rows:
            result.append(rows)

    return result


def parse_attendance_records(html: str) -> list[dict[str, Any]]:
    """Extracts course attendance records and computes safe bunks & recovery metrics."""
    tables = parse_generic_tables(html)
    records: list[dict[str, Any]] = []

    for table in tables:
        for row in table:
            # Find relevant columns by fuzzy header match
            code = ""
            name = ""
            conducted = 0
            attended = 0
            percentage = 0.0

            for k, v in row.items():
                k_lower = k.lower()
                if "code" in k_lower or "course id" in k_lower or "subject code" in k_lower:
                    code = v
                elif "title" in k_lower or "name" in k_lower or "course" in k_lower:
                    name = v
                elif (
                    "conducted" in k_lower
                    or "total" in k_lower
                    or "held" in k_lower
                    or "classes" in k_lower
                ):
                    try:
                        conducted = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        conducted = 0
                elif "attended" in k_lower or "present" in k_lower:
                    try:
                        attended = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        attended = 0
                elif "%" in k_lower or "percent" in k_lower:
                    try:
                        percentage = float(re.sub(r"[^\d.]", "", v) or "0.0")
                    except ValueError:
                        percentage = 0.0

            # If percentage is missing or 0 but conducted > 0, compute it
            if percentage == 0.0 and conducted > 0:
                percentage = round((attended / conducted) * 100.0, 2)

            # Check if this row looks like a course attendance row
            if code or name or conducted > 0:
                # Calculate safe bunks and recovery classes for 85% goal
                safe_bunks = 0
                recovery_needed = 0
                if conducted > 0:
                    if percentage >= 85.0:
                        safe_bunks = max(0, math.floor((attended - 0.85 * conducted) / 0.85))
                    else:
                        recovery_needed = max(0, math.ceil((0.85 * conducted - attended) / 0.15))

                status = "SAFE"
                if percentage < 75.0:
                    status = "CRITICAL"
                elif percentage < 85.0:
                    status = "WARNING"

                records.append(
                    {
                        "course_code": code,
                        "course_name": name,
                        "conducted": conducted,
                        "attended": attended,
                        "percentage": percentage,
                        "safe_bunks": safe_bunks,
                        "recovery_needed": recovery_needed,
                        "status": status,
                    }
                )

    return records


def parse_marks_records(html: str) -> list[dict[str, Any]]:
    """Extracts internal exam marks and component scores from ERP HTML."""
    tables = parse_generic_tables(html)
    records: list[dict[str, Any]] = []

    for table in tables:
        for row in table:
            c_code = ""
            c_name = ""
            component = ""
            max_marks = 0.0
            secured_marks = 0.0

            for k, v in row.items():
                k_lower = k.lower()
                if "code" in k_lower or "subject" in k_lower:
                    c_code = v
                elif "name" in k_lower or "title" in k_lower or "course" in k_lower:
                    c_name = v
                elif "component" in k_lower or "eval" in k_lower or "exam" in k_lower:
                    component = v
                elif "max" in k_lower or "total" in k_lower:
                    try:
                        max_marks = float(re.sub(r"[^\d.]", "", v) or "0")
                    except ValueError:
                        max_marks = 0.0
                elif "secured" in k_lower or "marks" in k_lower or "obtained" in k_lower:
                    try:
                        secured_marks = float(re.sub(r"[^\d.]", "", v) or "0")
                    except ValueError:
                        secured_marks = 0.0

            if c_code or c_name or component or secured_marks > 0:
                pct = round((secured_marks / max_marks * 100), 2) if max_marks > 0 else 0.0
                records.append(
                    {
                        "course_code": c_code,
                        "course_name": c_name,
                        "component": component or "Internal",
                        "max_marks": max_marks,
                        "secured_marks": secured_marks,
                        "percentage": pct,
                    }
                )

    return records


def parse_fee_records(html: str) -> list[dict[str, Any]]:
    """Extracts student fee order details and payment history."""
    tables = parse_generic_tables(html)
    records: list[dict[str, Any]] = []

    for table in tables:
        for row in table:
            order_id = ""
            term = ""
            amount = ""
            status = "UNKNOWN"
            date_str = ""

            for k, v in row.items():
                k_lower = k.lower()
                if "order" in k_lower or "receipt" in k_lower or "ref" in k_lower:
                    order_id = v
                elif "term" in k_lower or "year" in k_lower or "sem" in k_lower:
                    term = v
                elif "amount" in k_lower or "fee" in k_lower or "total" in k_lower:
                    amount = v
                elif "status" in k_lower:
                    status = v.upper()
                elif "date" in k_lower:
                    date_str = v

            if order_id or amount:
                records.append(
                    {
                        "order_id": order_id,
                        "term": term,
                        "amount": amount,
                        "status": status,
                        "date": date_str,
                    }
                )

    return records
