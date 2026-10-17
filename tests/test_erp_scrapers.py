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

