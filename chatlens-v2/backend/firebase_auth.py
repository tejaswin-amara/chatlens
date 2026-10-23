"""Firebase Authentication helper for ChatLens v2 Backend."""

import os
from typing import Any

from fastapi import Header, HTTPException, status

admin_auth: Any = None
try:
    import firebase_admin  # type: ignore[import-untyped,import-not-found]
    from firebase_admin import (  # type: ignore[import-untyped,import-not-found]
        auth as _auth,
    )
    from firebase_admin import (
        credentials,
    )

    admin_auth = _auth
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    HAS_FIREBASE = True
except Exception:
    HAS_FIREBASE = False


async def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any] | None:
    """Validate Firebase ID token from Authorization header (Bearer <token>).

    In offline/testing environments without firebase_admin configured, supports
    a mock token `Bearer mock-test-token` returning a test user profile.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    bearer_token = authorization.split("Bearer ", 1)[1]
    is_test_env = os.getenv("ENVIRONMENT") == "test" or os.getenv("TESTING") == "1"

    if not HAS_FIREBASE:
        if bearer_token == "mock-test-token":  # noqa: S105
            return {"uid": "test-user-123", "email": "tester@example.com"}
        return None

    if bearer_token == "mock-test-token":  # noqa: S105
        if is_test_env:
            return {"uid": "test-user-123", "email": "tester@example.com"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mock tokens are prohibited in non-test environments",
        )

    try:
        decoded: dict[str, Any] = admin_auth.verify_id_token(bearer_token)
        return decoded
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase authentication token",
        ) from err


async def require_current_user(
    authorization: str | None = Header(None),
) -> dict[str, Any] | None:
    """Enforce Firebase authentication when required by configuration."""
    user = await get_current_user(authorization)
    if user is None:
        require_auth = (
            os.getenv("REQUIRE_AUTH", "false").lower() in ("1", "true")
            or os.getenv("ENVIRONMENT") == "production"
        )
        if require_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided or are invalid",
            )
    return user
