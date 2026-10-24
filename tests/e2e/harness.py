"""E2E Test Harness for ChatLens v2 & SPARK PA Daemon.

Provides:
- Opaque-box E2E HTTP client supporting both offline simulation and live cluster execution.
- Reverse proxy routing simulator adhering to Caddy and Nginx specifications.
- Static asset serving simulator adhering to frontend/out build artifacts and nginx.conf.
- Compose, Caddyfile, and Nginx config parsers without external YAML dependencies.
- In-memory database and isolated SPARK SQLite fixtures.
"""

from __future__ import annotations

import mimetypes
import os
import re
import sqlite3
import sys
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "chatlens-v2" / "backend"
FRONTEND_OUT = PROJECT_ROOT / "chatlens-v2" / "frontend" / "out"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import celery_worker
    from database import get_db
    from fastapi.testclient import TestClient
    from models import Base

    import main
except ImportError as e:
    raise RuntimeError(f"Failed to import backend modules: {e}") from e

_ = celery_worker


class AsyncSessionMock:
    """Async wrapper around a synchronous SQLAlchemy Session for offline testing."""

    def __init__(self, sync_session: Session) -> None:
        self._s = sync_session
        self.bind = sync_session.bind

    async def execute(self, stmt: Any) -> Any:
        return self._s.execute(stmt)

    async def scalar(self, stmt: Any) -> Any:
        return self._s.scalar(stmt)

    async def commit(self) -> None:
        self._s.commit()

    async def rollback(self) -> None:
        self._s.rollback()

    async def close(self) -> None:
        pass


class CaseInsensitiveHeaderDict(dict):
    """Case-insensitive dictionary for HTTP headers."""

    def get(self, key: str, default: Any = None) -> Any:
        lower_key = key.lower()
        for k, v in self.items():
            if k.lower() == lower_key:
                return v
        return default

    def __getitem__(self, key: str) -> Any:
        lower_key = key.lower()
        for k, v in self.items():
            if k.lower() == lower_key:
                return v
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            lower_key = key.lower()
            return any(k.lower() == lower_key for k in self.keys())
        return False


@dataclass
class E2EResponse:
    status_code: int
    headers: CaseInsensitiveHeaderDict
    content: bytes
    text: str

    def json(self) -> Any:
        import json

        return json.loads(self.text)


class ComposeParser:
    """Lightweight pure-python parser for compose.yaml configurations."""

    @staticmethod
    def parse(file_path: Path | str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {}

        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        anchors: dict[str, Any] = {}
        root: dict[str, Any] = {}
        stack: list[tuple[Any, int, str | None]] = [(root, -1, None)]

        for raw_line in lines:
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())
            stripped = line.strip()

            while stack and indent <= stack[-1][1]:
                stack.pop()

            parent, _, current_key = stack[-1]

            if stripped.startswith("- "):
                val_str = stripped[2:].strip()
                if not isinstance(parent, list):
                    continue

                if ":" in val_str and not val_str.startswith(('"', "'")):
                    k, v = val_str.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    sub_item: dict[str, Any] = {k: ComposeParser._cast_value(v)}
                    parent.append(sub_item)
                    stack.append((sub_item, indent, k))
                else:
                    parent.append(ComposeParser._cast_value(val_str.strip("\"'")))
            elif ":" in stripped:
                k, v = stripped.split(":", 1)
                k = k.strip()
                v = v.strip()

                anchor_match = re.search(r"&([a-zA-Z0-9_-]+)", k)
                if anchor_match:
                    k = k.split("&")[0].strip()

                if v.startswith("*"):
                    alias_name = v[1:].strip()
                    resolved = anchors.get(alias_name, {})
                    if isinstance(parent, dict):
                        parent[k] = resolved.copy() if isinstance(resolved, dict) else resolved
                    continue

                if not v:
                    new_container: dict[str, Any] | list[Any] = {}
                    if isinstance(parent, dict):
                        parent[k] = new_container
                    elif isinstance(parent, list) and current_key:
                        pass
                    stack.append((new_container, indent, k))
                    if anchor_match:
                        anchors[anchor_match.group(1)] = new_container
                else:
                    val = ComposeParser._cast_value(v.strip("\"'"))
                    if isinstance(parent, dict):
                        parent[k] = val
                    if anchor_match:
                        anchors[anchor_match.group(1)] = val

        return root

    @staticmethod
    def _cast_value(v: str) -> Any:
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        if v.isdigit():
            return int(v)
        if v.startswith("[") and v.endswith("]"):
            return [item.strip().strip("\"'") for item in v[1:-1].split(",") if item.strip()]
        return v


class CaddyfileParser:
    """Parser for Caddyfile reverse proxy blocks."""

    @staticmethod
    def parse(file_path: Path | str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {}

        with open(path, encoding="utf-8") as f:
            content = f.read()

        handles: list[dict[str, str]] = []
        for match in re.finditer(r"handle(?:\s+([^\s{]+))?\s*\{([^}]+)\}", content):
            pattern = match.group(1) or "/*"
            body = match.group(2).strip()
            proxy_match = re.search(r"reverse_proxy\s+([^\s\n]+)", body)
            upstream = proxy_match.group(1) if proxy_match else ""
            handles.append({"pattern": pattern, "upstream": upstream, "raw": body})

        encodes = re.findall(r"encode\s+([^\n]+)", content)
        return {
            "handles": handles,
            "encodes": encodes[0].split() if encodes else [],
            "raw": content,
        }


class NginxConfParser:
    """Parser for frontend nginx.conf."""

    @staticmethod
    def parse(file_path: Path | str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {}

        with open(path, encoding="utf-8") as f:
            content = f.read()

        locations: list[dict[str, Any]] = []
        for match in re.finditer(r"location\s+([^{]+)\{([^}]+)\}", content):
            loc_path = match.group(1).strip()
            body = match.group(2).strip()
            try_files = re.findall(r"try_files\s+([^;]+);", body)
            cache_control = re.findall(r'add_header\s+Cache-Control\s+"([^"]+)";', body)
            expires = re.findall(r"expires\s+([^;]+);", body)
            locations.append(
                {
                    "location": loc_path,
                    "try_files": try_files[0].strip() if try_files else None,
                    "cache_control": cache_control[0] if cache_control else None,
                    "expires": expires[0] if expires else None,
                    "raw": body,
                }
            )

        error_pages = re.findall(r"error_page\s+([^;]+);", content)
        return {"locations": locations, "error_pages": error_pages, "raw": content}


class E2EClient:
    """Opaque-box HTTP client for E2E testing with dual live/offline capability."""

    def __init__(
        self,
        base_url: str | None = None,
        live: bool = False,
        engine: Any = None,
        spark_db: Path | str | None = None,
    ) -> None:
        self.live = live or (os.getenv("LIVE_E2E") == "1")
        self.base_url = base_url or os.getenv("BASE_URL", "http://localhost")
        self.engine = engine
        self.spark_db = spark_db

        if not self.live:
            self._asgi_client = TestClient(
                main.app,
                base_url="http://chatlens-backend:8000",
            )
        else:
            self._live_client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: Any = None,
        json: Any = None,
        files: Any = None,
    ) -> E2EResponse:
        headers = dict(headers or {})
        headers.setdefault("Host", "localhost")

        if self.live:
            res = self._live_client.request(
                method=method,
                url=path,
                headers=headers,
                params=params,
                data=data,
                json=json,
                files=files,
            )
            return E2EResponse(
                status_code=res.status_code,
                headers=CaseInsensitiveHeaderDict(res.headers),
                content=res.content,
                text=res.text,
            )

        # Offline Reverse Proxy Dispatcher simulation
        # Caddy rules: /api/* -> backend, /ws* -> backend, everything else -> frontend
        clean_path = path.split("?")[0]

        if clean_path.startswith("/api/") or clean_path == "/api" or clean_path.startswith("/ws"):
            headers.setdefault("X-Forwarded-For", "127.0.0.1")
            headers.setdefault("X-Forwarded-Proto", "http")

            res = self._asgi_client.request(
                method=method,
                url=path,
                headers=headers,
                params=params,
                data=data,
                json=json,
                files=files,
            )
            return E2EResponse(
                status_code=res.status_code,
                headers=CaseInsensitiveHeaderDict(res.headers),
                content=res.content,
                text=res.text,
            )

        # Frontend Static Dispatcher (Nginx container simulation)
        if method not in ("GET", "HEAD"):
            return E2EResponse(
                status_code=405,
                headers=CaseInsensitiveHeaderDict({"Content-Type": "text/plain"}),
                content=b"Method Not Allowed",
                text="Method Not Allowed",
            )

        # Path traversal guard
        if ".." in clean_path:
            return E2EResponse(
                status_code=404,
                headers=CaseInsensitiveHeaderDict({"Content-Type": "text/html; charset=utf-8"}),
                content=b"404 Not Found",
                text="404 Not Found",
            )

        rel_path = clean_path.lstrip("/")
        target_file: Path | None = None

        if rel_path == "" or rel_path == "index.html":
            target_file = FRONTEND_OUT / "index.html"
        elif rel_path.startswith("_next/static/"):
            target_file = FRONTEND_OUT / rel_path
        elif rel_path == "favicon.ico":
            target_file = FRONTEND_OUT / "favicon.ico"
        elif "." in Path(rel_path).name:
            target_file = FRONTEND_OUT / rel_path
        else:
            # SPA route fallback: try_files $uri $uri.html $uri/ /index.html =404
            cand = FRONTEND_OUT / f"{rel_path}.html"
            if cand.exists():
                target_file = cand
            else:
                target_file = FRONTEND_OUT / "index.html"

        if target_file and target_file.exists() and target_file.is_file():
            content = target_file.read_bytes()
            mime, _ = mimetypes.guess_type(str(target_file))
            mime = mime or "application/octet-stream"
            resp_headers: dict[str, str] = {"Content-Type": mime}

            if clean_path.startswith("/_next/static/"):
                resp_headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                resp_headers["Cache-Control"] = "no-cache"

            return E2EResponse(
                status_code=200,
                headers=CaseInsensitiveHeaderDict(resp_headers),
                content=content,
                text=content.decode("utf-8", errors="replace"),
            )
        elif not FRONTEND_OUT.exists() and (rel_path == "" or rel_path == "index.html"):
            mock_html = (
                b"<!doctype html><html><head><title>ChatLens</title></head>"
                b'<body><div id="root">ChatLens SPA</div></body></html>'
            )
            return E2EResponse(
                status_code=200,
                headers=CaseInsensitiveHeaderDict(
                    {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"}
                ),
                content=mock_html,
                text=mock_html.decode("utf-8"),
            )

        # 404 handler
        not_found_file = FRONTEND_OUT / "404.html"
        err_content = not_found_file.read_bytes() if not_found_file.exists() else b"404 Not Found"
        return E2EResponse(
            status_code=404,
            headers=CaseInsensitiveHeaderDict({"Content-Type": "text/html; charset=utf-8"}),
            content=err_content,
            text=err_content.decode("utf-8", errors="replace"),
        )

    def get(
        self,
        path: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> E2EResponse:
        return self.request("GET", path, headers=headers, params=params)

    def post(
        self,
        path: str,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        headers: dict[str, str] | None = None,
    ) -> E2EResponse:
        return self.request("POST", path, headers=headers, json=json, data=data, files=files)

    def put(
        self,
        path: str,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> E2EResponse:
        return self.request("PUT", path, headers=headers, json=json, data=data)

    def delete(self, path: str, headers: dict[str, str] | None = None) -> E2EResponse:
        return self.request("DELETE", path, headers=headers)


def setup_in_memory_backend_db():
    """Sets up an isolated in-memory SQLite backend database with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    db_lock = threading.Lock()

    def override_get_db():
        with db_lock:
            session = Session(engine)
            try:
                yield AsyncSessionMock(session)
            finally:
                session.close()

    @asynccontextmanager
    async def override_async_session_local():
        with db_lock:
            session = Session(engine)
            try:
                yield AsyncSessionMock(session)
            finally:
                session.close()

    main.app.dependency_overrides[get_db] = override_get_db
    return engine, override_get_db, override_async_session_local


def setup_isolated_spark_db(db_path: Path) -> sqlite3.Connection:
    """Sets up an isolated SQLite database matching SPARK PA daemon schema in WAL mode."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS seen (key TEXT PRIMARY KEY, ts REAL);")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pending ("
        "id INTEGER PRIMARY KEY, ts REAL, status TEXT, event_json TEXT);"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS writes ("
        "id INTEGER PRIMARY KEY, ts REAL, kind TEXT, event_id TEXT, undone INTEGER DEFAULT 0);"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chat_state ("
        "chat_id TEXT PRIMARY KEY, last_seen_msg_id INTEGER, updated_at REAL);"
    )
    conn.commit()
    return conn
