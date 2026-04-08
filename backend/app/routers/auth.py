import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.garmin_client import initialize_garmin_client, is_auth_ready

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthStatus(BaseModel):
    authenticated: bool
    message: str


@router.post("/retry", response_model=AuthStatus)
async def retry_auth() -> AuthStatus:
    """
    Trigger a fresh Garmin authentication attempt without restarting the server.
    Returns 200 on success or 503 if authentication still fails.
    """
    try:
        await asyncio.to_thread(initialize_garmin_client)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Authentication failed: {exc}",
        ) from exc

    return AuthStatus(authenticated=True, message="Garmin authentication successful")


@router.get("/status", response_model=AuthStatus)
async def auth_status() -> AuthStatus:
    """Return the current authentication state without triggering a login."""
    if is_auth_ready():
        return AuthStatus(authenticated=True, message="Garmin session is active")
    return AuthStatus(
        authenticated=False,
        message="Garmin authentication pending — POST /api/auth/retry to authenticate",
    )
