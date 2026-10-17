import type { ScraperSession, LoginResult } from '@/lib/scraper';
import type { AttendanceSubject, FeeItem } from '@/lib/ai/tools';

export const DEMO_SESSION: ScraperSession = {
  cookies: [{ name: 'PHPSESSID', value: 'demo_phpsessid_123' }],
  csrfToken: 'demo_csrf_token_123',
  userAgent:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
};

export const DEMO_ATTENDANCE: AttendanceSubject[] = [
  {
    'Course Code': '23CS2101R',
    'Course Title': 'Data Structures & Algorithms',
    Component: 'Lecture',
    'Conducted Hours': '45',
    'Attended Hours': '40',
    'Attendance Percentage': '88.89%',
    'Academic Year': '2025-2026',
    Semester: '1',
  },
  {
    'Course Code': '23CS2102R',
    'Course Title': 'Computer Organization & Architecture',
    Component: 'Lecture',
    'Conducted Hours': '40',
    'Attended Hours': '36',
    'Attendance Percentage': '90.00%',
    'Academic Year': '2025-2026',
    Semester: '1',
  },
  {
    'Course Code': '23CS2103R',
    'Course Title': 'Database Management Systems',
    Component: 'Lecture',
    'Conducted Hours': '42',
    'Attended Hours': '38',
    'Attendance Percentage': '90.48%',
    'Academic Year': '2025-2026',
    Semester: '1',
  },
  {
    'Course Code': '23CS2104R',
    'Course Title': 'Operating Systems',
    Component: 'Lecture',
    'Conducted Hours': '40',
    'Attended Hours': '33',
    'Attendance Percentage': '82.50%',
    'Academic Year': '2025-2026',
    Semester: '1',
  },
];

export const DEMO_TIMETABLE_RAW = [
  {
    'Day / Period': 'Monday',
    '1': '23CS2101R-L - S-10 - RoomNo-101 - Dr. Smith',
    '2': '23CS2102R-P - S-10 - RoomNo-LAB-3 - Prof. Johnson',
    '3': 'Free',
    '4': '23CS2103R-L - S-10 - RoomNo-105 - Dr. Allen',
  },
  {
    'Day / Period': 'Tuesday',
    '1': '23CS2102R-L - S-10 - RoomNo-102 - Prof. Johnson',
    '2': '23CS2101R-P - S-10 - RoomNo-LAB-1 - Dr. Smith',
    '3': 'Free',
    '4': '23CS2103R-P - S-10 - RoomNo-LAB-2 - Dr. Allen',
  },
  {
    'Day / Period': 'Wednesday',
    '1': '23CS2103R-L - S-10 - RoomNo-105 - Dr. Allen',
    '2': '23CS2101R-L - S-10 - RoomNo-101 - Dr. Smith',
    '3': '23CS2104R-L - S-10 - RoomNo-102 - Prof. Davis',
  },
  {
    'Day / Period': 'Thursday',
    '1': '23CS2101R-P - S-10 - RoomNo-LAB-1 - Dr. Smith',
    '2': '23CS2103R-P - S-10 - RoomNo-LAB-2 - Dr. Allen',
  },
  {
    'Day / Period': 'Friday',
    '1': '23CS2102R-P - S-10 - RoomNo-LAB-3 - Prof. Johnson',
    '2': '23CS2104R-L - S-10 - RoomNo-101 - Prof. Davis',
  },
];

export const DEMO_MARKS = [
  {
    'Course Code': '23CS2101R',
    'Course Name': 'Data Structures & Algorithms',
    'Faculty Name': 'Dr. Smith',
    'Internal 1': '22',
    'Internal 2': '24',
    Assignment: '10',
    'Total Marks': '56',
  },
  {
    'Course Code': '23CS2102R',
    'Course Name': 'Computer Organization & Architecture',
    'Faculty Name': 'Prof. Johnson',
    'Internal 1': '20',
    'Internal 2': '23',
    Assignment: '9',
    'Total Marks': '52',
  },
  {
    'Course Code': '23CS2103R',
    'Course Name': 'Database Management Systems',
    'Faculty Name': 'Dr. Allen',
    'Internal 1': '23',
    'Internal 2': '25',
    Assignment: '10',
    'Total Marks': '58',
  },
  {
    'Course Code': '23CS2104R',
    'Course Name': 'Operating Systems',
    'Faculty Name': 'Prof. Davis',
    'Internal 1': '21',
    'Internal 2': '22',
    Assignment: '9',
    'Total Marks': '52',
  },
];

export const DEMO_FEE_ITEMS: FeeItem[] = [
  {
    'Fee Type': 'Tuition Fee',
    Amount: '150000',
    'Paid Amount': '150000',
    'Balance Amount': '0',
    Status: 'PAID',
  },
  {
    'Fee Type': 'Special Skill Fee',
    Amount: '15,000',
    'Paid Amount': '10,000',
    'Balance Amount': '5,000',
    Status: 'PENDING',
  },
  {
    'Fee Type': 'Hostel & Mess Fee',
    Amount: '45,000',
    'Paid Amount': '35,000',
    'Balance Amount': '10,000',
    Status: 'PENDING',
  },
];

export const DEMO_PROFILE = {
  name: 'Alex Student',
  universityId: '2100030000',
  photoUrl: '/logo.png',
  program: 'B.Tech Computer Science & Engineering',
  department: 'Computer Science',
  academicYear: '2025-2026',
  semester: '1',
  extendedProfile: {
    'Personal Information': [
      { Field: 'Name', Value: 'Alex Student' },
      { Field: 'University ID', Value: '2100030000' },
      { Field: 'Program', Value: 'B.Tech Computer Science & Engineering' },
      { Field: 'Department', Value: 'Computer Science' },
    ],
    courses: [
      {
        Coursecode: '23CS2101R',
        Coursedesc: 'Data Structures & Algorithms',
        FacultyName: 'Dr. Smith',
      },
      {
        Coursecode: '23CS2102R',
        Coursedesc: 'Computer Organization & Architecture',
        FacultyName: 'Prof. Johnson',
      },
      {
        Coursecode: '23CS2103R',
        Coursedesc: 'Database Management Systems',
        FacultyName: 'Dr. Allen',
      },
    ],
  },
};

export const DEMO_CGPA = [
  {
    'Academic Year': '2025-2026',
    Semester: '1',
    SGPA: '9.20',
    CGPA: '9.15',
    Credits: '42',
    'Credits Completed': '42',
  },
];

export const DEMO_CAPTCHA_SVG =
  'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMjAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCAxMjAgNDAiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiNmZmZmZmYiLz48cGF0aCBkPSJNMCwyMCBRMzAsNSA2MCwyMCBUMTIwLDIwIiBzdHJva2U9IiNlMGUwZTAiIHN0cm9rZS13aWR0aD0iMS41IiBmaWxsPSJub25lIi8+PHBhdGggZD0iTTAsMTAgUTQwLDMwIDgwLDEwIFQxMjAsMzAiIHN0cm9rZT0iI2Q1ZDVkNSIgc3Ryb2tlLXdpZHRoPSIxLjUiIGZpbGw9Im5vbmUiLz48dGV4dCB4PSI1MCUiIHk9IjU1JSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Im1vbm9zcGFjZSwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIyMiIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IiMxMTExMTEiIGxldHRlci1zcGFjaW5nPSIzIj5hYmNkPC90ZXh0Pjwvc3ZnPg==';

export const DEMO_LOGIN_RESULT: LoginResult = {
  success: true,
  message: 'Login successful (Demo/Fallback Mode)',
  session: DEMO_SESSION,
  csrfToken: 'demo_csrf_token_123',
  academicYears: [
    { value: '2025-2026', label: '2025-2026' },
    { value: '2024-2025', label: '2024-2025' },
  ],
  semesters: [
    { value: '1', label: 'Odd Semester' },
    { value: '2', label: 'Even Semester' },
  ],
  deviceId: 'demo_device_123',
  needsCaptchaRetry: false,
};
