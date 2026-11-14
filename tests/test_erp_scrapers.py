"""Unit tests for KLU ERP scrapers and attendance margin calculations."""

from src.erp.scrapers import (
    parse_attendance_records,
    parse_cgpa_records,
    parse_fee_records,
    parse_generic_tables,
    parse_marks_records,
    parse_timetable_records,
)

SAMPLE_ATTENDANCE_HTML = """
<html>
<body>
    <table class="table table-bordered">
        <thead>
            <tr>
                <th>Course Code</th>
                <th>Course Title</th>
                <th>Conducted</th>
                <th>Attended</th>
                <th>Percentage</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>25CS2103E</td>
                <td>Data Structures & Algorithms-3</td>
                <td>40</td>
                <td>38</td>
                <td>95.00%</td>
            </tr>
            <tr>
                <td>25CS2104E</td>
                <td>Operating Systems & Systems Programming</td>
                <td>36</td>
                <td>30</td>
                <td>83.33%</td>
            </tr>
            <tr>
                <td>25SC2107E</td>
                <td>Machine Learning</td>
                <td>30</td>
                <td>21</td>
                <td>70.00%</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

SAMPLE_MARKS_HTML = """
<html>
<body>
    <table class="items table">
        <thead>
            <tr>
                <th>Course Code</th>
                <th>Course Name</th>
                <th>Component</th>
                <th>Max Marks</th>
                <th>Secured Marks</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>25CS2103E</td>
                <td>DSA-3</td>
                <td>Mid-Term 1</td>
                <td>30</td>
                <td>27.5</td>
            </tr>
            <tr>
                <td>25EC2206E</td>
                <td>ESD & IoT</td>
                <td>In-Sem Lab Exam</td>
                <td>50</td>
                <td>48</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

SAMPLE_FEE_HTML = """
<html>
<body>
    <table class="fee-table">
        <thead>
            <tr>
                <th>Order ID</th>
                <th>Academic Year / Term</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Payment Date</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>ORD-2026-9912</td>
                <td>2026-27 T04</td>
                <td>Rs. 1,35,000</td>
                <td>PAID</td>
                <td>2026-08-10</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


def test_parse_generic_tables() -> None:
    tables = parse_generic_tables(SAMPLE_ATTENDANCE_HTML)
    assert len(tables) == 1
    rows = tables[0]
    assert len(rows) == 3
    assert rows[0]["Course Code"] == "25CS2103E"
    assert rows[0]["Attended"] == "38"


def test_parse_attendance_metrics() -> None:
    records = parse_attendance_records(SAMPLE_ATTENDANCE_HTML)
    assert len(records) == 3

    # DSA3: 38/40 = 95% -> SAFE, has safe bunks
    dsa = records[0]
    assert dsa["course_code"] == "25CS2103E"
    assert dsa["conducted"] == 40
    assert dsa["attended"] == 38
    assert dsa["percentage"] == 95.0
    assert dsa["status"] == "SAFE"
    assert dsa["safe_bunks"] > 0
    assert dsa["recovery_needed"] == 0

    # OSSP: 30/36 = 83.33% -> WARNING, needs recovery classes
    ossp = records[1]
    assert ossp["course_code"] == "25CS2104E"
    assert ossp["percentage"] == 83.33
    assert ossp["status"] == "WARNING"
    assert ossp["safe_bunks"] == 0
    assert ossp["recovery_needed"] > 0

    # ML: 21/30 = 70.0% -> CRITICAL (<75%)
    ml = records[2]
    assert ml["course_code"] == "25SC2107E"
    assert ml["status"] == "CRITICAL"
    assert ml["recovery_needed"] > 0


def test_parse_marks() -> None:
    records = parse_marks_records(SAMPLE_MARKS_HTML)
    assert len(records) == 2
    assert records[0]["course_code"] == "25CS2103E"
    assert records[0]["component"] == "Mid-Term 1"
    assert records[0]["max_marks"] == 30.0
    assert records[0]["secured_marks"] == 27.5
    assert records[0]["percentage"] == 91.67

    assert records[1]["course_code"] == "25EC2206E"
    assert records[1]["secured_marks"] == 48.0
    assert records[1]["percentage"] == 96.0


def test_parse_fee() -> None:
    records = parse_fee_records(SAMPLE_FEE_HTML)
    assert len(records) == 1
    fee = records[0]
    assert fee["order_id"] == "ORD-2026-9912"
    assert fee["term"] == "2026-27 T04"
    assert fee["status"] == "PAID"
    assert "1,35,000" in fee["amount"]


def test_parse_klu_live_format_attendance() -> None:
    html = """
    <table>
        <thead>
            <tr>
                <th>#</th><th>Coursecode</th><th>Coursedesc</th><th>Ltps</th><th>Section</th>
                <th>Year</th><th>Semester</th><th>Fr Date</th><th>Total Conducted</th>
                <th>Total Attended</th><th>Total Absent</th><th>Tcbr</th><th>Percentage</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1</td><td>25CS1302E</td><td>DATABASE SYSTEMS</td><td>L</td>
                <td>S-10-MA</td><td>2026-2027</td><td>Odd Sem</td><td>N</td>
                <td>19</td><td>18</td><td>1</td><td>0</td><td>95%</td>
            </tr>
            <tr>
                <td>2</td><td>25SC2107E</td><td>MACHINE LEARNING</td><td>P</td>
                <td>S-10-A</td><td>2026-2027</td><td>Odd Sem</td><td>N</td>
                <td>21</td><td>19</td><td>2</td><td>0</td><td>91%</td>
            </tr>
        </tbody>
    </table>
    """
    records = parse_attendance_records(html)
    assert len(records) == 2
    assert records[0]["course_code"] == "25CS1302E"
    assert records[0]["ltps"] == "L"
    assert records[0]["section"] == "S-10-MA"
    assert records[0]["conducted"] == 19
    assert records[0]["attended"] == 18
    assert records[0]["absent"] == 1
    assert records[0]["percentage"] == 95.0
    assert records[0]["safe_bunks"] == 2

    assert records[1]["course_code"] == "25SC2107E"
    assert records[1]["ltps"] == "P"
    assert records[1]["conducted"] == 21
    assert records[1]["attended"] == 19
    assert records[1]["percentage"] == 91.0


def test_parse_cgpa() -> None:
    html = """
    <table>
        <thead>
            <tr>
                <th>#</th><th>University Id</th><th>Student Name</th><th>Course Code</th>
                <th>Course Name</th><th>Grade</th><th>Grade Point</th><th>Credits</th>
                <th>Promotion</th><th>Reg Academic Year</th><th>Reg Sem</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1</td><td>2520090104</td><td>TEJASWIN AMARA</td><td>25CS1201E</td>
                <td>FRONT END DEVELOPMENT FRAMEWORKS</td><td>O</td><td>10</td><td>3</td>
                <td>P</td><td>2025-2026</td><td>Term3</td>
            </tr>
        </tbody>
    </table>
    """
    records = parse_cgpa_records(html)
    assert len(records) == 1
    assert records[0]["course_code"] == "25CS1201E"
    assert records[0]["grade"] == "O"
    assert records[0]["grade_point"] == "10"
    assert records[0]["credits"] == "3"
    assert records[0]["semester"] == "Term3"


def test_parse_timetable() -> None:
    html = """
    <table>
        <thead>
            <tr>
                <th>Oday</th><th>1</th><th>2</th><th>3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Mon</td>
                <td>25CS1302E-L - S-10 -RoomNo-H-005</td>
                <td>-</td>
                <td>25EC2206E-S - S-11 -RoomNo-H301A</td>
            </tr>
        </tbody>
    </table>
    """
    records = parse_timetable_records(html)
    assert len(records) == 2
    assert records[0]["day"] == "Mon"
    assert records[0]["period"] == 1
    assert records[0]["course_code"] == "25CS1302E"
    assert records[0]["component"] == "L"
    assert records[0]["section"] == "S-10"
    assert records[0]["room"] == "H-005"

    assert records[1]["day"] == "Mon"
    assert records[1]["period"] == 3
    assert records[1]["course_code"] == "25EC2206E"
    assert records[1]["component"] == "S"
    assert records[1]["section"] == "S-11"
    assert records[1]["room"] == "H301A"


def test_compute_remaining_classes() -> None:
    from datetime import date

    from src.erp.scrapers import compute_remaining_classes

    # For DLAC (25CS3112E) between 2026-11-14 and 2027-01-28 (T05 term)
    rem = compute_remaining_classes(
        course_code="25CS3112E",
        course_name="Deep Learning With Accelerated Computing",
        ref_date=date(2026, 11, 14),
        last_instruction_day=date(2027, 1, 28),
    )
    assert rem > 0

    # Past instruction date returns 0
    rem_past = compute_remaining_classes(
        course_code="25CS3112E",
        ref_date=date(2027, 2, 1),
        last_instruction_day=date(2027, 1, 28),
    )
    assert rem_past == 0


def test_parse_attendance_hard_detention_flag() -> None:
    html = """
    <table>
        <thead>
            <tr>
                <th>Course Code</th>
                <th>Course Title</th>
                <th>Conducted</th>
                <th>Attended</th>
                <th>Percentage</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>25SC2107E</td><td>Machine Learning</td><td>40</td><td>15</td><td>37.5%</td>
            </tr>
        </tbody>
    </table>
    """
    # recovery needed for 85%: ceil((85*40 - 100*15)/15) = ceil(1900/15) = 127 classes
    # If remaining classes is only 10, recovery is impossible -> hard_detention is True
    records = parse_attendance_records(html, remaining_classes_map={"25SC2107E": 10})
    assert len(records) == 1
    rec = records[0]
    assert rec["course_code"] == "25SC2107E"
    assert rec["attended"] == 15
    assert rec["conducted"] == 40
    assert rec["recovery_needed"] > 100
    assert rec["remaining_classes"] == 10
    assert rec["hard_detention"] is True
    assert rec["detention_lockout"] is True
    assert rec["status"] == "CRITICAL"


def test_parse_attendance_safe_within_remaining() -> None:
    html = """
    <table>
        <thead>
            <tr>
                <th>Course Code</th>
                <th>Course Title</th>
                <th>Conducted</th>
                <th>Attended</th>
                <th>Percentage</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>25CS3112E</td><td>DLAC</td><td>10</td><td>8</td><td>80.0%</td>
            </tr>
        </tbody>
    </table>
    """
    # recovery needed for 85%: ceil((85*10 - 100*8)/15) = ceil(50/15) = 4 classes
    # If remaining classes is 30, recovery is easily achievable -> hard_detention is False
    records = parse_attendance_records(html, remaining_classes_map={"25CS3112E": 30})
    assert len(records) == 1
    rec = records[0]
    assert rec["recovery_needed"] == 4
    assert rec["remaining_classes"] == 30
    assert rec["hard_detention"] is False
    assert rec["detention_lockout"] is False
    assert rec["status"] == "WARNING"


def test_html_table_parser_colspan_grid() -> None:
    from src.erp.scrapers import parse_generic_tables

    html = """
    <table>
        <thead>
            <tr>
                <th>Day</th>
                <th>Period 1</th>
                <th>Period 2</th>
                <th>Period 3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Mon</td>
                <td colspan="2">25CS3112E Lab Workshop</td>
                <td>25CS2206E Lecture</td>
            </tr>
        </tbody>
    </table>
    """
    tables = parse_generic_tables(html)
    assert len(tables) == 1
    row = tables[0][0]
    assert row["Day"] == "Mon"
    # Period 1 and Period 2 both hold the spanned cell text without shifting Period 3
    assert row["Period 1"] == "25CS3112E Lab Workshop"
    assert row["Period 2"] == "25CS3112E Lab Workshop"
    assert row["Period 3"] == "25CS2206E Lecture"


def test_html_table_parser_rowspan_grid() -> None:
    from src.erp.scrapers import parse_generic_tables

    html = """
    <table>
        <thead>
            <tr>
                <th>Day</th>
                <th>Slot</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="2">Tue</td>
                <td>Period 1</td>
            </tr>
            <tr>
                <td>Period 2</td>
            </tr>
        </tbody>
    </table>
    """
    tables = parse_generic_tables(html)
    assert len(tables) == 1
    rows = tables[0]
    assert len(rows) == 2
    assert rows[0]["Day"] == "Tue"
    assert rows[0]["Slot"] == "Period 1"
    assert rows[1]["Day"] == "Tue"
    assert rows[1]["Slot"] == "Period 2"


def test_parse_hall_ticket_records() -> None:
    from src.erp.scrapers import parse_hall_ticket_records

    html = """
    <html>
    <body>
        <div class="student-header">
            <p>University Id: 2520090104</p>
            <p>Student Name: TEJASWIN AMARA</p>
            <p>Program: B.Tech Computer Science & Engineering</p>
            <p>Academic Year: 2026-2027</p>
            <p>Term: Trimester 5</p>
            <p>Exam Center: KLEF Vaddeswaram Campus</p>
        </div>
        <table class="table exam-table">
            <thead>
                <tr>
                    <th>Course Code</th>
                    <th>Course Name</th>
                    <th>Exam Date</th>
                    <th>Session</th>
                    <th>Room No</th>
                    <th>Seat No</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>25CS3112E</td>
                    <td>Deep Learning With Accelerated Computing</td>
                    <td>2027-01-25</td>
                    <td>09:30 AM - 12:30 PM</td>
                    <td>H-005</td>
                    <td>D-14</td>
                </tr>
                <tr>
                    <td>25CS2206E</td>
                    <td>Cloud Infrastructure And Services</td>
                    <td>2027-01-27</td>
                    <td>09:30 AM - 12:30 PM</td>
                    <td>H-201</td>
                    <td>B-08</td>
                </tr>
            </tbody>
        </table>
        <ul class="instructions">
            <li>1. Candidates must carry their valid University ID Card and Hall Ticket.</li>
            <li>2. Electronic gadgets including smartwatches are strictly prohibited.</li>
        </ul>
    </body>
    </html>
    """
    ht = parse_hall_ticket_records(html)
    assert ht["student_id"] == "2520090104"
    assert ht["student_name"] == "TEJASWIN AMARA"
    assert ht["academic_year"] == "2026-2027"
    assert "Trimester 5" in ht["term"]
    assert "KLEF" in ht["exam_center"]
    assert len(ht["exam_schedule"]) == 2
    sched1 = ht["exam_schedule"][0]
    assert sched1["course_code"] == "25CS3112E"
    assert sched1["exam_date"] == "2027-01-25"
    assert sched1["room_no"] == "H-005"
    assert sched1["seat_no"] == "D-14"
    assert len(ht["instructions"]) >= 1
