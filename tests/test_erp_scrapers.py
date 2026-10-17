"""Unit tests for KLU ERP scrapers and attendance margin calculations."""

from src.erp.scrapers import (
    parse_attendance_records,
    parse_fee_records,
    parse_generic_tables,
    parse_marks_records,
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
