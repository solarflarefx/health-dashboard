"""
Garmin Connect client singleton.

Login strategy
--------------
1. Always try to restore an existing session from the token store first.
   This is fast and avoids sending credentials over the wire on every restart.
2. Only fall back to a full credential login when no valid tokens exist.
3. On HTTP 429 (rate-limit), back off exponentially before retrying:
   60 s → 120 s → give up (max 3 total attempts).

Startup grace period
--------------------
If authentication fails at startup the server does NOT crash.
`_auth_ready` stays False; `get_garmin_client()` raises
`GarminNotAuthenticatedError`, which the metrics router converts to 503.
Call `initialize_garmin_client()` again (via POST /api/auth/retry) to retry
without restarting the process.
"""

import logging
import time
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

from app.config import TOKEN_STORE_PATH, settings

logger = logging.getLogger(__name__)

_client: Garmin | None = None
_auth_ready: bool = False

_BACKOFF_BASE_SECONDS = 60
_BACKOFF_MAX_ATTEMPTS = 3


# ─── Public exception ─────────────────────────────────────────────────────────


class GarminNotAuthenticatedError(Exception):
    """Raised by get_garmin_client() when the session is not yet established."""


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _new_garmin_instance() -> Garmin:
    return Garmin(
        email=settings.garmin_email,
        password=settings.garmin_password,
        is_cn=False,
        prompt_mfa=None,
    )


def _token_store_has_tokens() -> bool:
    """Return True if the token store directory exists and contains at least one file."""
    return TOKEN_STORE_PATH.exists() and any(TOKEN_STORE_PATH.iterdir())


def _try_restore_session(client: Garmin) -> bool:
    """
    Attempt to restore an OAuth session from disk.
    Returns True on success, False if no tokens exist or they are invalid/expired.
    """
    if not _token_store_has_tokens():
        logger.info("Token store is empty — skipping restore attempt")
        return False
    try:
        client.login(str(TOKEN_STORE_PATH))
        logger.info("Garmin session restored from token store at %s", TOKEN_STORE_PATH)
        return True
    except Exception as exc:
        logger.info("Token restore failed (%s) — will attempt full login", exc)
        return False


def _full_login_with_backoff(client: Garmin) -> None:
    """
    Perform a credential-based login with exponential backoff on 429 responses.
    Raises the last exception if all attempts are exhausted.
    """
    delay = _BACKOFF_BASE_SECONDS
    for attempt in range(1, _BACKOFF_MAX_ATTEMPTS + 1):
        try:
            client.login()
            return
        except GarminConnectTooManyRequestsError:
            if attempt == _BACKOFF_MAX_ATTEMPTS:
                logger.error(
                    "Garmin returned 429 on attempt %d/%d — giving up",
                    attempt,
                    _BACKOFF_MAX_ATTEMPTS,
                )
                raise
            logger.warning(
                "Garmin returned 429 (attempt %d/%d) — retrying in %d s",
                attempt,
                _BACKOFF_MAX_ATTEMPTS,
                delay,
            )
            time.sleep(delay)
            delay *= 2


# ─── Public API ───────────────────────────────────────────────────────────────


def initialize_garmin_client() -> None:
    """
    Initialise (or re-initialise) the Garmin client.

    Called once at startup and again via POST /api/auth/retry.
    On failure, leaves _auth_ready=False so the server continues running
    and endpoints return 503 until a subsequent call succeeds.
    """
    global _client, _auth_ready

    TOKEN_STORE_PATH.mkdir(parents=True, exist_ok=True)
    client = _new_garmin_instance()

    if _try_restore_session(client):
        _client = client
        _auth_ready = True
        return

    logger.info("No valid tokens — performing full credential login")
    try:
        _full_login_with_backoff(client)
        client.garth.dump(str(TOKEN_STORE_PATH))
        _client = client
        _auth_ready = True
        logger.info("Full login succeeded; tokens saved to %s", TOKEN_STORE_PATH)
    except Exception as exc:
        _auth_ready = False
        logger.warning("Garmin authentication failed on init: %s", exc)
        raise


def get_garmin_client() -> Garmin:
    """
    Return the authenticated Garmin client.
    Raises GarminNotAuthenticatedError if the session has not been established yet.
    """
    if not _auth_ready or _client is None:
        raise GarminNotAuthenticatedError(
            "Garmin authentication pending — please try again shortly"
        )
    return _client


def refresh_garmin_client() -> None:
    """
    Force a fresh full login and update the singleton.
    Called by the auth-retry decorator in services/garmin.py when a mid-request
    GarminConnectAuthenticationError is received.
    """
    global _client, _auth_ready
    logger.warning("Refreshing Garmin session after authentication error")

    client = _new_garmin_instance()
    try:
        _full_login_with_backoff(client)
        client.garth.dump(str(TOKEN_STORE_PATH))
        _client = client
        _auth_ready = True
        logger.info("Garmin session refreshed successfully")
    except Exception as exc:
        _auth_ready = False
        logger.error("Garmin session refresh failed: %s", exc)
        raise


def is_auth_ready() -> bool:
    """Return True if the client is authenticated and ready to serve requests."""
    return _auth_ready
