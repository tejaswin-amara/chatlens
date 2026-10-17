"""Firebase Authentication helper for ChatLens v2 Backend."""

import os
from typing import Any

from fastapi import Header, HTTPException, status

admin_auth: Any = None
try:
    import firebase_admin  # type: ignore[import-untyped,import-not-found]
    from firebase_admin import (  # type: ignore[import-untyped,import-not-found]
        auth as _auth,
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

    token = authorization.split("Bearer ", 1)[1]
    if not HAS_FIREBASE:
        if token == "mock-test-token":
            return {"uid": "test-user-123", "email": "tester@example.com"}
        return None

    try:
        decoded: dict[str, Any] = admin_auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase authentication token",
        )
