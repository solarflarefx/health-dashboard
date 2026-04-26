"""
Garmin Connect client singleton.

Login strategy
--------------
1. Always try to restore an existing session from the token store first.
   This is fast and avoids sending credentials over the wire on every restart.
   Garminconnect 0.3.2 handles this automatically when a tokenstore path is
   passed to login(): it loads existing tokens, proactively refreshes them if
   expiring soon, and verifies auth by fetching the social profile.
2. Only fall back to a full credential login when no valid tokens exist or
   token load/validation fails (garminconnect handles this internally).
3. The library's 5-strategy chain (mobile+cffi, mobile+requests, widget+cffi,
   portal+cffi, portal+requests) handles 429 rate limits internally.
   We additionally apply exponential backoff at the outer level if all
   strategies are simultaneously rate-limited (GarminConnectTooManyRequestsError).

Token storage
-------------
Tokens are stored as JSON at TOKEN_STORE_PATH/garmin_tokens.json.
The new native auth engine (0.3.2) uses di_token/di_refresh_token format;
old garth-format tokens are incompatible and should be deleted before use.

Startup grace period
--------------------
If authentication fails at startup the server does NOT crash.
`_auth_ready` stays False; `get_garmin_client()` raises
`GarminNotAuthenticatedError`, which the metrics router converts to 503.
Call `initialize_garmin_client()` again (via POST /api/auth/retry) to retry
without restarting the process.
"""

import logging
import sys
import time
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from app.config import TOKEN_STORE_PATH, settings

logger = logging.getLogger(__name__)

_client: Garmin | None = None
_auth_ready: bool = False

_BACKOFF_BASE_SECONDS = 60
_BACKOFF_MAX_ATTEMPTS = 3

# Relative path within TOKEN_STORE_PATH where the library writes tokens.
_TOKEN_FILE = "garmin_tokens.json"


# ─── Public exception ─────────────────────────────────────────────────────────


class GarminNotAuthenticatedError(Exception):
    """Raised by get_garmin_client() when the session is not yet established."""


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _prompt_mfa() -> str:
    """
    MFA callback passed to garminconnect.

    Invoked synchronously from the worker thread that runs initialize_garmin_client()
    (dispatched via asyncio.to_thread in main.py), so it blocks only that thread —
    the event loop stays free while waiting for the user to type.

    We read from /dev/tty directly instead of stdin so that the prompt works
    even when uvicorn has redirected stdin (e.g. when started as a background
    process or under a process supervisor).  Falls back to input() on platforms
    without /dev/tty (Windows).
    """
    print(
        "\nGarmin MFA required — open your authenticator app and enter the 6-digit code:",
        flush=True,
    )
    try:
        with open("/dev/tty") as tty:
            sys.stderr.write("MFA code: ")
            sys.stderr.flush()
            return tty.readline().strip()
    except OSError:
        return input("MFA code: ").strip()


def _new_garmin_instance() -> Garmin:
    return Garmin(
        email=settings.garmin_email,
        password=settings.garmin_password,
        is_cn=False,
        prompt_mfa=_prompt_mfa,
    )


def _login_with_backoff(garmin: Garmin, tokenstore: str | None = None) -> None:
    """
    Call garmin.login() with exponential backoff on GarminConnectTooManyRequestsError.

    The library's 5-strategy chain already handles per-strategy 429s internally;
    this outer backoff only fires when every strategy simultaneously returns 429.

    Args:
        garmin: An initialised Garmin instance.
        tokenstore: Path passed through to login().  When set, the library
                    tries to restore tokens from there and, on a fresh
                    credential login, auto-saves the new tokens.

    Raises:
        GarminConnectTooManyRequestsError: if all retries are exhausted.
        GarminConnectAuthenticationError: on wrong credentials / MFA required.
        GarminConnectConnectionError: on unrecoverable transport failure.
    """
    delay = _BACKOFF_BASE_SECONDS
    for attempt in range(1, _BACKOFF_MAX_ATTEMPTS + 1):
        try:
            garmin.login(tokenstore)
            return
        except GarminConnectTooManyRequestsError:
            if attempt == _BACKOFF_MAX_ATTEMPTS:
                logger.error(
                    "Garmin returned 429 on all strategies (attempt %d/%d) — giving up",
                    attempt,
                    _BACKOFF_MAX_ATTEMPTS,
                )
                raise
            logger.warning(
                "Garmin returned 429 on all strategies (attempt %d/%d) — retrying in %d s",
                attempt,
                _BACKOFF_MAX_ATTEMPTS,
                delay,
            )
            time.sleep(delay)
            delay *= 2


def _clear_token_file() -> None:
    """Delete the cached token file so the next login is forced to use credentials."""
    token_path = TOKEN_STORE_PATH / _TOKEN_FILE
    if token_path.exists():
        try:
            token_path.unlink()
            logger.info("Cleared stale token file at %s", token_path)
        except OSError as exc:
            logger.warning("Could not remove stale token file: %s", exc)


# ─── Public API ───────────────────────────────────────────────────────────────


def initialize_garmin_client() -> None:
    """
    Initialise (or re-initialise) the Garmin client.

    Called once at startup and again via POST /api/auth/retry.
    On failure, leaves _auth_ready=False so the server continues running
    and endpoints return 503 until a subsequent call succeeds.

    garminconnect 0.3.2: login(tokenstore) handles token restore → credential
    fallback → auto-save all in one call.
    """
    global _client, _auth_ready

    TOKEN_STORE_PATH.mkdir(parents=True, exist_ok=True)
    garmin = _new_garmin_instance()

    try:
        _login_with_backoff(garmin, tokenstore=str(TOKEN_STORE_PATH))
        _client = garmin
        _auth_ready = True
        logger.info("Garmin authenticated successfully (tokens at %s)", TOKEN_STORE_PATH)
    except (
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    ) as exc:
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
    Force a fresh full credential login and update the singleton.

    Called by the auth-retry decorator in services/garmin.py when a mid-request
    GarminConnectAuthenticationError is received.

    We delete the stale token file first so that login() cannot load invalid
    tokens — without this, the library would raise on the post-load profile
    check instead of falling through to credential login.
    """
    global _client, _auth_ready
    logger.warning("Refreshing Garmin session after authentication error")

    _clear_token_file()
    garmin = _new_garmin_instance()
    try:
        _login_with_backoff(garmin, tokenstore=str(TOKEN_STORE_PATH))
        _client = garmin
        _auth_ready = True
        logger.info("Garmin session refreshed successfully; tokens saved to %s", TOKEN_STORE_PATH)
    except (
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    ) as exc:
        _auth_ready = False
        logger.error("Garmin session refresh failed: %s", exc)
        raise


def is_auth_ready() -> bool:
    """Return True if the client is authenticated and ready to serve requests."""
    return _auth_ready
