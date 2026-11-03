# Koneru Lakshmaiah Education Foundation (KL Deemed to be University)
## Y25 B.Tech Trimester Program — Academic Calendar 2026–2027

Authoritative academic schedule and institutional milestones for the second-year (Y25) undergraduate engineering program operating on the PBL Trimester model.

---

### Term Overview

| Term | Duration | Classwork Commencement | End of Term |
| :--- | :--- | :--- | :--- |
| **Trimester-4 (T04)** | 13-Jul-2026 to 01-Nov-2026 | 23-Jul-2026 | 01-Nov-2026 |
| **Trimester-5 (T05)** | 04-Nov-2026 to 07-Feb-2027 | 04-Nov-2026 | 07-Feb-2027 |
| **Trimester-6 (T06)** | 09-Feb-2027 to 09-May-2027 | 09-Feb-2027 | 09-May-2027 |
| **Summer Term** | 31-May-2027 to 11-Jul-2027 | 31-May-2027 | 11-Jul-2027 |

---

### Trimester-4 (T04) Milestone Schedule

| Event / Milestone | Start Date | End Date | Invariant 5 Protected |
| :--- | :--- | :--- | :--- |
| T4-Orientation & Registrations | 13-Jul-2026 | 18-Jul-2026 | Yes |
| Commencement of Classwork | 23-Jul-2026 | 23-Jul-2026 | Yes |
| MID TERM Exams (Along with Class work) | 04-Sep-2026 | 08-Sep-2026 | Yes |
| Last Date to Request Re-Check for MID TERM Exams | 12-Sep-2026 | 12-Sep-2026 | Yes |
| Last Date to Pay End Exam Fee | 26-Sep-2026 | 26-Sep-2026 | Yes |
| Lab Exams Along with Class work | 12-Oct-2026 | 17-Oct-2026 | Yes |
| Last Instruction Day | 15-Oct-2026 | 15-Oct-2026 | Yes |
| Declaration of Detention List | 16-Oct-2026 | 16-Oct-2026 | Yes |
| SEM END Lab Exams | 19-Oct-2026 | 24-Oct-2026 | Yes |
| SEM End Theory Exams + Hackathon | 26-Oct-2026 | 01-Nov-2026 | Yes |

---

### Trimester-5 (T05) Milestone Schedule

| Event / Milestone | Start Date | End Date | Invariant 5 Protected |
| :--- | :--- | :--- | :--- |
| T5-Orientation & Registrations | 05-Oct-2026 | 07-Oct-2026 | Yes |
| Techno-Management Immersion Week | 30-Oct-2026 | 31-Oct-2026 | No |
| Commencement of Classwork | 04-Nov-2026 | 04-Nov-2026 | Yes |
| MID TERM Exams (Along with Class work) | 14-Dec-2026 | 19-Dec-2026 | Yes |
| Last Date to Request Re-Check for MID TERM Exams | 24-Dec-2026 | 24-Dec-2026 | Yes |
| Last Date to Pay End Exam Fee | 09-Jan-2027 | 09-Jan-2027 | Yes |
| Lab Exams Along with Class work | 18-Jan-2027 | 23-Jan-2027 | Yes |
| SEM END Lab Exams | 25-Jan-2027 | 30-Jan-2027 | Yes |
| Last Instruction Day | 28-Jan-2027 | 28-Jan-2027 | Yes |
| Declaration of Detention List | 29-Jan-2027 | 29-Jan-2027 | Yes |
| SEM End Theory Exams + Hackathon | 01-Feb-2027 | 07-Feb-2027 | Yes |

---

### Trimester-6 (T06) Milestone Schedule

| Event / Milestone | Start Date | End Date | Invariant 5 Protected |
| :--- | :--- | :--- | :--- |
| T6-Orientation & Registrations | 25-Jan-2027 | 27-Jan-2027 | Yes |
| Commencement of Classwork | 09-Feb-2027 | 09-Feb-2027 | Yes |
| Cultural Immersion Week | 12-Mar-2027 | 13-Mar-2027 | No |
| MID TERM Exams (Along with Class work) | 22-Mar-2027 | 27-Mar-2027 | Yes |
| Last Date to Request Re-Check for MID TERM Exams | 31-Mar-2027 | 31-Mar-2027 | Yes |
| Last Date to Pay End Exam Fee | 10-Apr-2027 | 10-Apr-2027 | Yes |
| Lab Exams Along with Class work | 19-Apr-2027 | 24-Apr-2027 | Yes |
| SEM END Lab Exams | 26-Apr-2027 | 01-May-2027 | Yes |
| Last Instruction Day | 29-Apr-2027 | 29-Apr-2027 | Yes |
| Declaration of Detention List | 30-Apr-2027 | 30-Apr-2027 | Yes |
| SEM End Theory Exams + Hackathon | 02-May-2027 | 09-May-2027 | Yes |

---

### Summer Term 2026–2027 Schedule

| Event / Milestone | Start Date | End Date | Invariant 5 Protected |
| :--- | :--- | :--- | :--- |
| 3-Week Summer Technical Internship | 10-May-2027 | 29-May-2027 | No |
| 8-Week Summer Internship | 10-May-2027 | 03-Jul-2027 | No |
| Summer Term Orientation & Registrations | 28-May-2027 | 29-May-2027 | Yes |
| Commencement of Summer Term Classwork | 31-May-2027 | 31-May-2027 | Yes |
| MID TERM Exams along with class work | 18-Jun-2027 | 19-Jun-2027 | Yes |
| 2027-28 Odd Semester Registrations | 28-Jun-2027 | 03-Jul-2027 | Yes |
| Lab In Sem Exams Along with Class Work | 29-Jun-2027 | 30-Jun-2027 | Yes |
| Declaration of Detention List | 07-Jul-2027 | 07-Jul-2027 | Yes |
| SEM End Theory Exams + Hackathon | 08-Jul-2027 | 11-Jul-2027 | Yes |
| 2027-28 Academic Year Commencement | 12-Jul-2027 | 12-Jul-2027 | Yes |

---

### SPARK Daemon Invariant 5 Governance Rules

1. **Non-Overridability**: Incoming Telegram messages (including faculty announcements or forwarded notices) are strictly forbidden from modifying official academic dates (exam periods, fee deadlines, detention list publication, and last instruction days).
2. **Conflict Detection**: When an extracted announcement claims an exam or deadline that contradicts the official calendar date range, SPARK flags `CALENDAR_CONFLICT`, suppresses automatic writes to Google Tasks and Google Calendar, and alerts the owner directly via the PA Bot.
3. **Data Source Integration**: Calendar configuration is maintained in `data/calendar_2026_27.toml` and queried via `src/academic_calendar.py`.
