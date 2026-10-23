"""Firebase authentication and production API access policy for ChatLens."""

import os
from typing import Any

from fastapi import Header, HTTPException, Request, status

admin_auth: Any = None
try:
    import firebase_admin  # type: ignore[import-untyped,import-not-found]
    from firebase_admin import auth as _auth  # type: ignore[import-untyped,import-not-found]
    from firebase_admin import credentials

    admin_auth = _auth
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path:
            if not os.path.isfile(cred_path):
                raise FileNotFoundError("FIREBASE_CREDENTIALS_PATH is not a readable file")
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        else:
            firebase_admin.initialize_app()
    HAS_FIREBASE = True
except Exception:
    HAS_FIREBASE = False


def _authentication_required() -> bool:
    return (
        os.getenv("REQUIRE_AUTH", "false").lower() in ("1", "true", "yes")
        or os.getenv("ENVIRONMENT", "").lower() == "production"
    )


async def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any] | None:
    """Validate a Firebase ID token from Authorization: Bearer <token>.

    The fixed mock token is accepted only in explicit test environments, never
    as a fallback for a missing or misconfigured Firebase Admin SDK.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    bearer_token = authorization.removeprefix("Bearer ").strip()
    is_test_env = os.getenv("ENVIRONMENT") == "test" or os.getenv("TESTING") == "1"

    if bearer_token == "mock-test-token":  # noqa: S105
        if is_test_env:
            return {"uid": "test-user-123", "email": "tester@example.com"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mock authentication tokens are only allowed in test environments",
        )

    if not HAS_FIREBASE:
        return None

    try:
        decoded: dict[str, Any] = admin_auth.verify_id_token(bearer_token)
        return decoded
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase authentication token",
        ) from err


async def require_current_user(
    request: Request,
    authorization: str | None = Header(None),
) -> dict[str, Any] | None:
    """Require an allowlisted Firebase user on non-probe API routes in production."""
    # Liveness must remain independent of Firebase and database availability.
    if request.url.path == "/api/healthz":
        return None

    user = await get_current_user(authorization)
    if not _authentication_required():
        return user

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid",
        )

    allowed_emails = {
        email.strip().casefold()
        for email in os.getenv("CHATLENS_ALLOWED_EMAILS", "").split(",")
        if email.strip()
    }
    if not allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is enabled but CHATLENS_ALLOWED_EMAILS is not configured",
        )

    email = user.get("email")
    if not isinstance(email, str) or email.casefold() not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not authorized to access this ChatLens instance",
        )

    return user
