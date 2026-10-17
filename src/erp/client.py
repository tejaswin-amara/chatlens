"""KLU ERP client for authenticating against newerp.kluniversity.in and scraping academic data."""

import asyncio
import json
import re
from typing import Any

import httpx

from src.config import settings
from src.erp.scrapers import (
    parse_attendance_records,
    parse_fee_records,
    parse_marks_records,
)
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger

logger = get_logger(__name__)

ERP_BASE_URL = "https://newerp.kluniversity.in"
LOGIN_URL = f"{ERP_BASE_URL}/index.php?r=site%2Flogin"
ATTENDANCE_URL = (
    f"{ERP_BASE_URL}/index.php?r=studentattendance%2Fstudentdailyattendance%2Fcourselist"
)
TIMETABLE_URL = (
    f"{ERP_BASE_URL}/index.php?r=timetables%2Funiversitymasteracademictimetableview"
    f"%2Findexstudentindisearch"
)
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
        self._load_cached_session()

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

                    # Successful login redirects away from site/login or contains dashboard markers
                    if "site/login" not in str(post_res.url) and (
                        "Dashboard" in post_res.text
                        or "Welcome" in post_res.text
                        or "Logout" in post_res.text
                    ):
                        self._cookies = {k: v for k, v in client.cookies.items()}
                        self._save_session()
                        logger.info("Successfully authenticated to KLU ERP", username=self.username)
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

    async def fetch_page(self, url: str) -> str:
        """Fetches an ERP page using authenticated session cookies."""
        async with self._get_http_client() as client:
            res = await client.get(url)
            # Check if redirected to login page
            if "site/login" in str(res.url) or "Please login" in res.text:
                logger.info("ERP session expired. Re-authenticating...")
                logged_in = await self.login()
                if not logged_in:
                    return ""
                # Retry with fresh cookies
                async with self._get_http_client() as fresh_client:
                    fresh_res = await fresh_client.get(url)
                    return fresh_res.text
            return res.text


    async def get_attendance(self) -> list[dict[str, Any]]:
        """Scrapes and returns verified course-wise attendance metrics."""
        html = await self.fetch_page(ATTENDANCE_URL)
        if not html:
            return []
        return parse_attendance_records(html)

    async def get_marks(self) -> list[dict[str, Any]]:
        """Scrapes and returns internal assessment marks."""
        html = await self.fetch_page(MARKS_URL)
        if not html:
            return []
        return parse_marks_records(html)

    async def get_fee_orders(self) -> list[dict[str, Any]]:
        """Scrapes and returns fee order payment records."""
        html = await self.fetch_page(FEE_URL)
        if not html:
            return []
        return parse_fee_records(html)


klu_erp = KLUERPClient()
