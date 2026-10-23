"""KLU ERP client for authenticating against newerp.kluniversity.in and scraping academic data."""

import asyncio
import contextlib
import json
import re
import sqlite3
import time
from typing import Any

import httpx

from src.config import settings
from src.erp.scrapers import (
    parse_attendance_records,
    parse_cgpa_records,
    parse_fee_records,
    parse_marks_records,
    parse_timetable_records,
)
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger

logger = get_logger(__name__)

ERP_BASE_URL = "https://newerp.kluniversity.in"
LOGIN_URL = f"{ERP_BASE_URL}/index.php?r=site%2Flogin"
ATTENDANCE_INPUT_URL = (
    f"{ERP_BASE_URL}/index.php?r=studentattendance%2Fstudentdailyattendance%2Fsearchgetinput"
)
ATTENDANCE_URL = (
    f"{ERP_BASE_URL}/index.php?r=studentattendance%2Fstudentdailyattendance%2Fcourselist"
)
TIMETABLE_URL = f"{ERP_BASE_URL}/index.php"
MARKS_URL = (
    f"{ERP_BASE_URL}/index.php?r=studentinfo%2Fstudentendexamresult%2Fgetstudentinternalmarks"
)
CGPA_URL = f"{ERP_BASE_URL}/index.php?r=studentinfo%2Fstudentendexamresult%2Fsearchgetmycgpa"
FEE_URL = f"{ERP_BASE_URL}/index.php?r=feepayments%2Fstudentfeeorderdetailsinfo%2Fmy_fee_orders"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class KLUERPClient:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        base_url: str = ERP_BASE_URL,
    ) -> None:
        self.username = username or settings.erp_username
        self.password = password or settings.erp_password.get_secret_value()
        self.base_url = base_url
        self._cookies: dict[str, str] = {}
        self._login_lock = asyncio.Lock()
        self._last_login_time: float = 0.0
        self._load_cached_session()

    def _save_marks_cache(
        self, academic_year: str, semester_id: str, records: list[dict[str, Any]]
    ) -> None:
        try:
            key = f"{academic_year}:{semester_id}"
            data_json = json.dumps(records)
            now = time.time()
            with contextlib.closing(
                sqlite3.connect(settings.spark_db, isolation_level=None)
            ) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS erp_marks_cache (
                        key TEXT PRIMARY KEY,
                        academic_year TEXT,
                        semester_id TEXT,
                        data TEXT,
                        updated REAL
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO erp_marks_cache
                    (key, academic_year, semester_id, data, updated)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, academic_year, semester_id, data_json, now),
                )
            deduplicator.meta_set("erp_marks_cache", data_json)
        except Exception as e:
            logger.debug("Failed to save marks cache", error=str(e))

    def _get_cached_marks(self, academic_year: str, semester_id: str) -> list[dict[str, Any]]:
        try:
            key = f"{academic_year}:{semester_id}"
            with contextlib.closing(
                sqlite3.connect(settings.spark_db, isolation_level=None)
            ) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS erp_marks_cache (
                        key TEXT PRIMARY KEY,
                        academic_year TEXT,
                        semester_id TEXT,
                        data TEXT,
                        updated REAL
                    )
                    """
                )
                row = conn.execute(
                    """
                    SELECT data FROM erp_marks_cache
                    WHERE key = ? OR (academic_year = ? AND semester_id = ?)
                    """,
                    (key, academic_year, semester_id),
                ).fetchone()
                if row and row[0]:
                    records = json.loads(row[0])
                    if isinstance(records, list):
                        return records
        except Exception as e:
            logger.debug("Failed to query erp_marks_cache table", error=str(e))

        cached = deduplicator.meta_get("erp_marks_cache")
        if cached:
            try:
                records = json.loads(cached)
                if isinstance(records, list):
                    return records
            except Exception as e:
                logger.debug("Failed to decode cached ERP marks from meta", error=str(e))
        return []

    def _load_cached_session(self) -> None:
        cached = deduplicator.meta_get("erp_session_cookies")
        if cached:
            try:
                self._cookies = json.loads(cached)
            except Exception:
                self._cookies = {}

    def _save_session(self) -> None:
        deduplicator.meta_set("erp_session_cookies", json.dumps(self._cookies))

    def _get_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            cookies=self._cookies,
            timeout=15.0,
            follow_redirects=True,
        )

    async def solve_captcha(self, image_bytes: bytes) -> str:
        """Solves the KLU ERP alphanumeric captcha using Gemini 3.5 Flash Lite Vision."""
        if not settings.gemini_api_key.get_secret_value():
            logger.warning("No Gemini API key configured for ERP captcha solving")
            return ""

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            prompt = (
                "You are an optical character recognition engine.\n"
                "Read the 4 to 6 characters displayed in this captcha image.\n"
                "Return ONLY the plain alphanumeric characters in lowercase "
                "without spaces or punctuation."
            )

            res = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=[image_part, prompt],
            )
            raw = (res.text or "").strip().lower()
            cleaned = re.sub(r"[^a-z0-9]", "", raw)
            logger.info("Solved ERP captcha", length=len(cleaned))
            return cleaned
        except Exception as e:
            logger.error("Failed to solve ERP captcha", error=str(e))
            return ""

    async def login(self, max_retries: int = 3) -> bool:
        """Logs into newerp.kluniversity.in with CSRF token extraction and captcha solving."""
        if not self.username or not self.password:
            logger.warning("Missing ERP credentials. Set ERP_USERNAME and ERP_PASSWORD in .env")
            return False

        start_wait = time.time()
        async with self._login_lock:
            if self._last_login_time > start_wait and self._cookies:
                logger.info("ERP session already refreshed by concurrent task")
                return True

            for attempt in range(1, max_retries + 1):
                try:
                    async with httpx.AsyncClient(
                        headers={"User-Agent": USER_AGENT}, timeout=15.0, follow_redirects=True
                    ) as client:
                        # 1. Fetch login page
                        login_res = await client.get(LOGIN_URL)
                        html = login_res.text

                        # 2. Extract CSRF token
                        csrf_match = re.search(
                            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']', html
                        )
                        csrf_token = csrf_match.group(1) if csrf_match else ""
                        if not csrf_token:
                            logger.error("Failed to find _csrf token in ERP login page")
                            return False

                        # 3. Extract Captcha image URL
                        captcha_match = re.search(
                            r'id=["\']loginFormCaptcha-image["\'][^>]*src=["\']([^"\']+)["\']', html
                        )
                        if not captcha_match:
                            logger.error("Failed to find captcha image element")
                            return False

                        captcha_src = captcha_match.group(1).replace("&amp;", "&")
                        if captcha_src.startswith("/"):
                            captcha_url = f"{self.base_url}{captcha_src}"
                        elif not captcha_src.startswith("http"):
                            captcha_url = f"{self.base_url}/{captcha_src}"
                        else:
                            captcha_url = captcha_src

                        # 4. Download captcha image
                        img_res = await client.get(captcha_url, headers={"Referer": LOGIN_URL})
                        captcha_solution = await self.solve_captcha(img_res.content)
                        if not captcha_solution:
                            logger.warning("Empty captcha solution", attempt=attempt)
                            continue

                        # 5. POST login credentials
                        form_data = {
                            "_csrf": csrf_token,
                            "LoginForm[username]": self.username,
                            "LoginForm[password]": self.password,
                            "LoginForm[captcha]": captcha_solution,
                            "LoginForm[rememberMe]": "1",
                            "login-button": "",
                        }

                        post_res = await client.post(
                            LOGIN_URL,
                            data=form_data,
                            headers={"Referer": LOGIN_URL},
                        )

                        # Successful login redirects away or contains dashboard markers
                        if "site/login" not in str(post_res.url) and (
                            "Dashboard" in post_res.text
                            or "Welcome" in post_res.text
                            or "Logout" in post_res.text
                        ):
                            self._cookies = {k: v for k, v in client.cookies.items()}
                            self._save_session()
                            self._last_login_time = time.time()
                            logger.info(
                                "Successfully authenticated to KLU ERP", username=self.username
                            )
                            return True

                        if "Incorrect username or password" in post_res.text:
                            logger.error("Invalid ERP username or password")
                            return False

                        logger.warning(
                            "ERP login attempt failed (possibly wrong captcha)", attempt=attempt
                        )

                except Exception as e:
                    logger.warning("ERP login attempt exception", attempt=attempt, error=str(e))

            return False

    def _is_session_expired(self, res: httpx.Response) -> bool:
        if res.status_code in (401, 403):
            return True
        url_str = str(res.url)
        if hasattr(res, "request") and res.request and (not url_str or url_str == "https://"):
            url_str = str(res.request.url)
        url_lower = url_str.lower()
        return (
            "site/login" in url_lower
            or "site%2flogin" in url_lower
            or "please login" in res.text.lower()
            or 'id="login-form"' in res.text
            or 'id="loginform-username"' in res.text
        )

    async def fetch_page(self, url: str) -> str:
        """Fetches an ERP page using authenticated session cookies."""
        async with self._get_http_client() as client:
            res = await client.get(url)
            if self._is_session_expired(res):
                logger.info("ERP session expired. Re-authenticating...")
                logged_in = await self.login()
                if not logged_in:
                    return ""
                async with self._get_http_client() as fresh_client:
                    fresh_res = await fresh_client.get(url)
                    return fresh_res.text
            return res.text

    async def get_attendance(
        self, academic_year: str = "29", semester_id: str = "1"
    ) -> list[dict[str, Any]]:
        """Scrapes and returns verified course-wise attendance metrics."""
        try:
            search_html = await self.fetch_page(ATTENDANCE_INPUT_URL)
            csrf_m = re.search(r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']', search_html)
            csrf = csrf_m.group(1) if csrf_m else ""

            async with self._get_http_client() as client:
                res = await client.post(
                    ATTENDANCE_URL,
                    data={
                        "_csrf": csrf,
                        "DynamicModel[academicyear]": academic_year,
                        "DynamicModel[semesterid]": semester_id,
                    },
                    headers={
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": ATTENDANCE_INPUT_URL,
                    },
                )
                if self._is_session_expired(res):
                    logger.info("ERP session expired during attendance query. Re-authenticating...")
                    if await self.login():
                        search_html = await self.fetch_page(ATTENDANCE_INPUT_URL)
                        csrf_m = re.search(
                            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']', search_html
                        )
                        csrf = csrf_m.group(1) if csrf_m else ""
                        async with self._get_http_client() as fresh_client:
                            res = await fresh_client.post(
                                ATTENDANCE_URL,
                                data={
                                    "_csrf": csrf,
                                    "DynamicModel[academicyear]": academic_year,
                                    "DynamicModel[semesterid]": semester_id,
                                },
                                headers={
                                    "X-Requested-With": "XMLHttpRequest",
                                    "Referer": ATTENDANCE_INPUT_URL,
                                },
                            )
                records = parse_attendance_records(res.text)
                if records:
                    deduplicator.meta_set("erp_attendance_cache", json.dumps(records))
                    return records
        except Exception as e:
            logger.error("Failed to query ERP attendance", error=str(e))

        cached = deduplicator.meta_get("erp_attendance_cache")
        if cached:
            try:
                return json.loads(cached)
            except Exception as e:
                logger.debug("Failed to decode cached ERP attendance", error=str(e))
        return []

    async def get_timetable(
        self, academic_year: str = "29", semester_id: str = "1"
    ) -> list[dict[str, Any]]:
        """Scrapes and returns official weekly timetable matrix from KLU ERP."""
        try:
            tt_route = (
                "timetables/universitymasteracademictimetableview/individualstudenttimetableget"
            )
            tt_url = (
                f"{TIMETABLE_URL}?r={tt_route}&"
                f"UniversityMasterAcademicTimetableView[academicyear]={academic_year}&"
                f"UniversityMasterAcademicTimetableView[semesterid]={semester_id}"
            )
            html = await self.fetch_page(tt_url)
            records = parse_timetable_records(html)
            if records:
                deduplicator.meta_set("erp_timetable_cache", json.dumps(records))
                return records
        except Exception as e:
            logger.error("Failed to query ERP timetable", error=str(e))

        cached = deduplicator.meta_get("erp_timetable_cache")
        if cached:
            try:
                return json.loads(cached)
            except Exception as e:
                logger.debug("Failed to decode cached ERP timetable", error=str(e))
        return []

    async def get_marks(
        self, academic_year: str = "29", semester_id: str = "1"
    ) -> list[dict[str, Any]]:
        """Scrapes and returns internal assessment marks."""
        try:
            marks_page = await self.fetch_page(MARKS_URL)
            csrf_m = re.search(r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']', marks_page)
            csrf = csrf_m.group(1) if csrf_m else ""

            async with self._get_http_client() as client:
                res = await client.post(
                    MARKS_URL,
                    data={
                        "_csrf": csrf,
                        "DynamicModel[academicyear]": academic_year,
                        "DynamicModel[semester]": semester_id,
                    },
                    headers={"Referer": MARKS_URL},
                )
                if self._is_session_expired(res):
                    logger.info("ERP session expired during marks query. Re-authenticating...")
                    if await self.login():
                        marks_page = await self.fetch_page(MARKS_URL)
                        csrf_m = re.search(
                            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']', marks_page
                        )
                        csrf = csrf_m.group(1) if csrf_m else ""
                        async with self._get_http_client() as fresh_client:
                            res = await fresh_client.post(
                                MARKS_URL,
                                data={
                                    "_csrf": csrf,
                                    "DynamicModel[academicyear]": academic_year,
                                    "DynamicModel[semester]": semester_id,
                                },
                                headers={"Referer": MARKS_URL},
                            )
                records = parse_marks_records(res.text)
                if records:
                    self._save_marks_cache(academic_year, semester_id, records)
                    return records
        except Exception as e:
            logger.error("Failed to query ERP marks", error=str(e))

        cached = self._get_cached_marks(academic_year, semester_id)
        if cached:
            return cached
        return []

    async def get_cgpa(self) -> list[dict[str, Any]]:
        """Scrapes and returns official academic grades, grade points and CGPA records."""
        try:
            html = await self.fetch_page(CGPA_URL)
            return parse_cgpa_records(html)
        except Exception as e:
            logger.error("Failed to query ERP CGPA", error=str(e))
            return []

    async def get_fee_orders(self) -> list[dict[str, Any]]:
        """Scrapes and returns fee order payment records."""
        try:
            html = await self.fetch_page(FEE_URL)
            if not html:
                return []
            return parse_fee_records(html)
        except Exception as e:
            logger.error("Failed to query ERP fee orders", error=str(e))
            return []


klu_erp = KLUERPClient()
