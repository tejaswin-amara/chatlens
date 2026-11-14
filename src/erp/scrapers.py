"""ERP HTML scrapers and data parsers using Python standard library html.parser."""

import math
import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


class HTMLTableParser(HTMLParser):
    """HTML Table parser supporting 2D coordinate grid tracking with colspan and rowspan."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._grid: dict[tuple[int, int], str] = {}
        self._row_idx: int = -1
        self._col_idx: int = 0
        self._current_cell: list[str] = []
        self._current_spans: tuple[int, int, int] = (1, 1, 0)
        self._in_cell: bool = False
        self._in_table: bool = False
        self._max_row: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower == "table":
            self._in_table = True
            self._grid = {}
            self._row_idx = -1
            self._col_idx = 0
            self._max_row = 0
        elif tag_lower == "tr":
            if self._in_table:
                self._row_idx += 1
                self._col_idx = 0
        elif tag_lower in ("td", "th"):
            if self._in_table:
                self._in_cell = True
                self._current_cell = []

                while (self._row_idx, self._col_idx) in self._grid:
                    self._col_idx += 1

                rowspan = 1
                colspan = 1
                for attr_name, attr_val in attrs:
                    if attr_name.lower() == "rowspan" and attr_val and attr_val.isdigit():
                        rowspan = max(1, int(attr_val))
                    elif attr_name.lower() == "colspan" and attr_val and attr_val.isdigit():
                        colspan = max(1, int(attr_val))

                self._current_spans = (rowspan, colspan, self._col_idx)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("td", "th"):
            if self._in_cell:
                self._in_cell = False
                cell_text = "".join(self._current_cell).strip()
                cell_text = re.sub(r"\s+", " ", cell_text)

                rowspan, colspan, col_start = self._current_spans
                for dr in range(rowspan):
                    r = self._row_idx + dr
                    for dc in range(colspan):
                        c = col_start + dc
                        self._grid[(r, c)] = cell_text
                    if r + 1 > self._max_row:
                        self._max_row = r + 1

                self._col_idx = col_start + colspan
        elif tag_lower == "tr":
            if self._in_table and self._row_idx + 1 > self._max_row:
                self._max_row = self._row_idx + 1
        elif tag_lower == "table":
            if self._in_table:
                self._in_table = False
                if self._grid:
                    max_c = max((c for (_, c) in self._grid), default=-1) + 1
                    table_matrix: list[list[str]] = []
                    for r in range(self._max_row):
                        row_cells = [self._grid.get((r, c), "") for c in range(max_c)]
                        if any(cell != "" for cell in row_cells):
                            table_matrix.append(row_cells)
                    if table_matrix:
                        self.tables.append(table_matrix)
                self._grid = {}

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


def compute_remaining_classes(
    course_code: str,
    course_name: str = "",
    ref_date: date | None = None,
    last_instruction_day: date | None = None,
) -> int:
    """Compute scheduled remaining classes for a course up to last_instruction_day."""
    from datetime import timedelta

    from src.utils import clock

    if ref_date is None:
        ref_date = clock.today_ist()

    if isinstance(ref_date, datetime):
        ref_date = ref_date.date()

    if isinstance(last_instruction_day, str):
        try:
            last_instruction_day = date.fromisoformat(last_instruction_day)
        except ValueError:
            last_instruction_day = None

    if last_instruction_day is None:
        try:
            from src.academic_calendar import get_milestone_date, load_calendar

            cal = load_calendar()
            if cal:
                last_instruction_day = get_milestone_date("last instruction", ref_date, cal)
        except Exception:
            last_instruction_day = None

    if last_instruction_day is None or ref_date > last_instruction_day:
        return 0

    # Attempt to load timetable slots to compute exact remaining periods
    try:
        from src.timetable import COURSE_INFO, COURSE_METADATA, load

        tt = load()
        if tt and tt.slots:
            clean_code = course_code.strip().upper()
            clean_name = course_name.strip().upper()

            matching_courses: set[str] = set()
            for key, (c_code, c_title) in COURSE_INFO.items():
                if (clean_code and clean_code == c_code.upper()) or (
                    clean_name and (clean_name in c_title.upper() or c_title.upper() in clean_name)
                ):
                    matching_courses.add(key.upper())

            for key, meta in COURSE_METADATA.items():
                if (clean_code and clean_code == meta.code.upper()) or (
                    clean_name
                    and (clean_name in meta.name.upper() or meta.name.upper() in clean_name)
                ):
                    matching_courses.add(key.upper())

            day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat"}
            slots_by_day: dict[str, int] = {d: 0 for d in day_map.values()}

            for slot in tt.slots:
                slot_c = slot.course.strip().upper()
                if (
                    slot_c in matching_courses
                    or (clean_code and clean_code in slot_c)
                    or (clean_name and slot_c in clean_name)
                ):
                    slots_by_day[slot.day] = slots_by_day.get(slot.day, 0) + 1

            total_remaining = 0
            curr = ref_date
            while curr <= last_instruction_day:
                d_name = day_map.get(curr.weekday())
                if d_name:
                    total_remaining += slots_by_day.get(d_name, 0)
                curr += timedelta(days=1)

            if total_remaining > 0 or matching_courses:
                return total_remaining
    except Exception as err:
        logger.debug("Timetable lookup failed for remaining classes", error=str(err))

    # Fallback estimate: 3 periods per week if term is active
    remaining_days = max(0, (last_instruction_day - ref_date).days)
    return (remaining_days // 7) * 3


def parse_attendance_records(
    html: str,
    ref_date: date | None = None,
    last_instruction_day: date | None = None,
    remaining_classes_map: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Extracts course attendance records and computes safe bunks & recovery metrics."""
    tables = parse_generic_tables(html)
    records: list[dict[str, Any]] = []

    for table in tables:
        for row in table:
            code = ""
            name = ""
            ltps = ""
            section = ""
            conducted = 0
            attended = 0
            absent = 0
            percentage = 0.0

            for k, v in row.items():
                k_lower = k.lower()
                is_code = (
                    "coursecode" in k_lower
                    or "course id" in k_lower
                    or "subject code" in k_lower
                    or ("code" in k_lower and "course" in k_lower)
                )
                is_name = (
                    "coursedesc" in k_lower
                    or "subject name" in k_lower
                    or ("course" in k_lower and "name" in k_lower)
                    or "title" in k_lower
                )
                if is_code:
                    code = v
                elif is_name:
                    name = v
                elif "ltps" in k_lower or "type" in k_lower:
                    ltps = v
                elif "section" in k_lower:
                    section = v
                elif "attended" in k_lower or "present" in k_lower:
                    try:
                        attended = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        attended = 0
                elif "absent" in k_lower:
                    try:
                        absent = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        absent = 0
                elif "conducted" in k_lower or "held" in k_lower:
                    try:
                        conducted = int(float(re.sub(r"[^\d.]", "", v) or "0"))
                    except ValueError:
                        conducted = 0
                elif "%" in k_lower or "percent" in k_lower:
                    try:
                        percentage = float(re.sub(r"[^\d.]", "", v) or "0.0")
                    except ValueError:
                        percentage = 0.0

            if not code and "code" in [k.lower() for k in row.keys()]:
                code = row.get("Code", row.get("code", ""))

            # If percentage is missing or 0 but conducted > 0, compute it
            if percentage == 0.0 and conducted > 0:
                percentage = round((attended / conducted) * 100.0, 2)

            # Check if this row looks like a course attendance row
            if code or name or conducted > 0:
                # Calculate safe bunks and recovery classes for 85% and 75% thresholds
                safe_bunks = 0
                safe_bunks_75 = 0
                recovery_needed = 0
                recovery_needed_75 = 0
                if conducted > 0:
                    if 100 * attended >= 85 * conducted:
                        safe_bunks = max(0, math.floor((100 * attended - 85 * conducted) / 85))
                    else:
                        recovery_needed = max(0, math.ceil((85 * conducted - 100 * attended) / 15))
                    if 100 * attended >= 75 * conducted:
                        safe_bunks_75 = max(0, math.floor((100 * attended - 75 * conducted) / 75))
                    else:
                        recovery_needed_75 = max(
                            0, math.ceil((75 * conducted - 100 * attended) / 25)
                        )

                status = "SAFE"
                if percentage < 75.0:
                    status = "CRITICAL"
                elif percentage < 85.0:
                    status = "WARNING"

                # Calculate remaining classes up to last_instruction_day
                if remaining_classes_map and code in remaining_classes_map:
                    rem_classes = remaining_classes_map[code]
                elif remaining_classes_map and name in remaining_classes_map:
                    rem_classes = remaining_classes_map[name]
                else:
                    rem_classes = compute_remaining_classes(
                        course_code=code,
                        course_name=name,
                        ref_date=ref_date,
                        last_instruction_day=last_instruction_day,
                    )

                # Flag hard detention lockout when recovery needed exceeds remaining classes
                hard_detention = bool(
                    rem_classes is not None
                    and (
                        (recovery_needed > 0 and recovery_needed > rem_classes)
                        or (recovery_needed_75 > 0 and recovery_needed_75 > rem_classes)
                    )
                )

                records.append(
                    {
                        "course_code": code,
                        "course_name": name,
                        "ltps": ltps,
                        "section": section,
                        "conducted": conducted,
                        "attended": attended,
                        "absent": absent,
                        "percentage": percentage,
                        "safe_bunks": safe_bunks,
                        "safe_bunks_85": safe_bunks,
                        "safe_bunks_75": safe_bunks_75,
                        "recovery_needed": recovery_needed,
                        "recovery_needed_75": recovery_needed_75,
                        "remaining_classes": rem_classes,
                        "hard_detention": hard_detention,
                        "detention_lockout": hard_detention,
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


def parse_cgpa_records(html: str) -> list[dict[str, Any]]:
    """Extracts official grade points, credits and semester results from CGPA portal."""
    tables = parse_generic_tables(html)
    records: list[dict[str, Any]] = []

    for table in tables:
        for row in table:
            c_code = ""
            c_name = ""
            grade = ""
            grade_point = ""
            credits = ""
            sem = ""
            acad_year = ""
            promotion = ""

            for k, v in row.items():
                k_lower = k.lower()
                if "course code" in k_lower or "code" in k_lower:
                    c_code = v
                elif "course name" in k_lower or "name" in k_lower:
                    c_name = v
                elif "grade point" in k_lower:
                    grade_point = v
                elif "grade" in k_lower:
                    grade = v
                elif "credit" in k_lower:
                    credits = v
                elif "promotion" in k_lower:
                    promotion = v
                elif "reg sem" in k_lower or "semester" in k_lower:
                    sem = v
                elif "academic year" in k_lower or "year" in k_lower:
                    acad_year = v

            if c_code and grade:
                records.append(
                    {
                        "course_code": c_code,
                        "course_name": c_name,
                        "grade": grade,
                        "grade_point": grade_point,
                        "credits": credits,
                        "promotion": promotion,
                        "semester": sem,
                        "academic_year": acad_year,
                    }
                )

    return records


def parse_timetable_records(html: str) -> list[dict[str, Any]]:
    """Extracts timetable slots from official KLU ERP weekly matrix."""
    tables = parse_generic_tables(html)
    records: list[dict[str, Any]] = []

    for table in tables:
        for row in table:
            day = row.get("Oday") or row.get("Day") or row.get("day", "")
            if not day:
                continue
            for col, val in row.items():
                if col.isdigit() and val and val != "-":
                    period_num = int(col)
                    match = re.match(
                        r"^([A-Z0-9]+)(?:-([A-Za-z]))?\s*-\s*(.*?)\s*-RoomNo-(.*)$", val
                    )
                    if match:
                        c_code, comp, sec, room = match.groups()
                        records.append(
                            {
                                "day": day,
                                "period": period_num,
                                "course_code": c_code,
                                "component": comp or "",
                                "section": sec.strip(),
                                "room": room.strip(),
                                "raw": val,
                            }
                        )
                    else:
                        records.append(
                            {
                                "day": day,
                                "period": period_num,
                                "raw": val,
                            }
                        )

    return records


def parse_hall_ticket_records(html: str) -> dict[str, Any]:
    """Extract official hall ticket metadata, student details, and exam schedule."""
    tables = parse_generic_tables(html)

    student_id = ""
    student_name = ""
    program = ""
    term = ""
    academic_year = ""
    exam_center = ""
    exam_schedule: list[dict[str, Any]] = []
    instructions: list[str] = []

    # 1. Regex search for student metadata in HTML
    id_m = re.search(
        r"(?:university\s*id|student\s*id|reg(?:istration)?\s*(?:no|number)|roll\s*no)[\s:]*([A-Za-z0-9]+)",
        html,
        re.IGNORECASE,
    )
    if id_m:
        student_id = id_m.group(1).strip()

    name_m = re.search(
        r"(?:student\s*name|name\s*of\s*the\s*candidate|candidate\s*name)[\s:]*([A-Za-z\s.]+?)(?:<|\n|$|degree|program|term)",
        html,
        re.IGNORECASE,
    )
    if name_m:
        student_name = re.sub(r"\s+", " ", name_m.group(1)).strip()

    prog_m = re.search(
        r"(?:program(?:me)?|degree|branch|department)[\s:]*([A-Za-z\s.&-]+?)(?:<|\n|$|year|sem)",
        html,
        re.IGNORECASE,
    )
    if prog_m:
        program = re.sub(r"\s+", " ", prog_m.group(1)).strip()

    term_m = re.search(
        r"(?:term|semester|reg\s*sem)[\s:]*([A-Za-z0-9\s-]+?)(?:<|\n|$|year)",
        html,
        re.IGNORECASE,
    )
    if term_m:
        term = term_m.group(1).strip()

    year_m = re.search(
        r"(?:academic\s*year|acad\s*year)[\s:]*([0-9]{4}\s*-\s*[0-9]{2,4})",
        html,
        re.IGNORECASE,
    )
    if year_m:
        academic_year = year_m.group(1).replace(" ", "")

    center_m = re.search(
        r"(?:exam\s*center|center|venue)[\s:]*([A-Za-z0-9\s,.-]+?)(?:<|\n|$)",
        html,
        re.IGNORECASE,
    )
    if center_m:
        exam_center = re.sub(r"\s+", " ", center_m.group(1)).strip()

    # 2. Extract exam schedule from parsed tables
    for table in tables:
        for row in table:
            c_code = ""
            c_name = ""
            e_date = ""
            e_time = ""
            room = ""
            seat = ""

            for k, v in row.items():
                k_lower = k.lower()
                if (
                    "course code" in k_lower
                    or "subject code" in k_lower
                    or k_lower in ("code", "course")
                ):
                    c_code = v
                elif (
                    "course name" in k_lower
                    or "course title" in k_lower
                    or "subject name" in k_lower
                ):
                    c_name = v
                elif "exam date" in k_lower or "date" in k_lower:
                    e_date = v
                elif "time" in k_lower or "session" in k_lower or "slot" in k_lower:
                    e_time = v
                elif "room" in k_lower or "hall" in k_lower:
                    room = v
                elif "seat" in k_lower or "desk" in k_lower:
                    seat = v
                elif "reg" in k_lower or "student id" in k_lower:
                    if not student_id and v:
                        student_id = v
                elif "student name" in k_lower:
                    if not student_name and v:
                        student_name = v

            if c_code or (e_date and (c_name or room)):
                exam_schedule.append(
                    {
                        "course_code": c_code,
                        "course_name": c_name,
                        "exam_date": e_date,
                        "exam_time": e_time,
                        "room_no": room,
                        "seat_no": seat,
                    }
                )

    # 3. Extract instructions / guidelines
    inst_matches = re.findall(
        r"(?:<li>|(?:\d+\.))\s*([A-Z][^<>\n]+?(?:hall\s*ticket|id\s*card|calculator|exam|entry|reporting|hours)[^<>\n]*)",
        html,
        re.IGNORECASE,
    )
    for inst in inst_matches:
        cleaned_inst = re.sub(r"\s+", " ", inst).strip()
        if len(cleaned_inst) > 10 and cleaned_inst not in instructions:
            instructions.append(cleaned_inst)

    return {
        "student_id": student_id,
        "student_name": student_name,
        "program": program,
        "term": term,
        "academic_year": academic_year,
        "exam_center": exam_center,
        "exam_schedule": exam_schedule,
        "instructions": instructions,
    }
