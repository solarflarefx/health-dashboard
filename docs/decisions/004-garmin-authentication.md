# ADR-004: Terminal-Based MFA for Garmin Login

## Status

Accepted

## Date

2026-04-08 (initial auth flow); 2026-04-25 (MFA prompt fix for real Garmin accounts)

## Context

Garmin Connect accounts with multi-factor authentication enabled require a one-time 6-digit TOTP code during login. The `garminconnect` library supports this via a `prompt_mfa` callback passed to the `Garmin` constructor.

Our usage model today is **local development only**: one developer, one machine, backend started from a terminal. After a successful login, session tokens persist under `.secrets/garmin/` (ADR-003) and subsequent restarts restore the session without re-entering credentials or MFA.

Constraints:

- MFA is synchronous and blocking — the user must type a code while the login is in progress.
- `uvicorn` may redirect stdin when run under a process supervisor or in certain IDE integrations, breaking a naive `input()` call.
- A deployed dashboard would need a different UX — users cannot be expected to watch the server terminal.

## Decision

**Terminal-based MFA prompt for local development.**

Implementation in `backend/app/garmin_client.py`:

- `_prompt_mfa()` is passed as `prompt_mfa` to `Garmin(...)`.
- It prints a message to stdout and reads the 6-digit code from `/dev/tty` (falls back to `input()` on platforms without `/dev/tty`, e.g. Windows).
- Login runs on a worker thread via `asyncio.to_thread(initialize_garmin_client)` in `main.py` startup and `POST /api/auth/retry`, so the MFA prompt blocks only that thread — the async event loop stays responsive.

**Auth endpoints that exist today:**

| Endpoint | Purpose |
|---|---|
| `GET /api/auth/status` | Report whether `_auth_ready` is true — no login triggered |
| `POST /api/auth/retry` | Re-run `initialize_garmin_client()` without restarting the server |

There is **no** `POST /api/auth/mfa` endpoint. The MFA code is collected entirely through the terminal callback, not through the REST API.

**Graceful degradation on startup failure:**

If Garmin auth fails at startup (wrong password, MFA timeout, 429 rate limit), the server still starts. Metrics endpoints return 503 until auth succeeds; the developer can fix credentials or enter MFA and call `POST /api/auth/retry`.

## Alternatives Considered

**Frontend MFA input via `POST /api/auth/mfa`.**

A natural choice for deployment: the dashboard shows an MFA input field, posts the code to the backend, and the backend passes it to `garminconnect`.

**Deferred** — local dev only needs MFA once per token lifetime (weeks or months), thanks to token persistence. Building a frontend MFA flow adds UI state, error handling, and security considerations (MFA codes in HTTP requests) before we have a deployment target. Revisit when the app moves off localhost.

**Disable MFA on the Garmin account.**

Rejected — weakens account security for a marginal convenience gain.

**Headless auth with pre-seeded tokens copied from another machine.**

Considered as a workaround during 429 debugging — rejected as a primary approach because tokens expire and the manual copy step is error-prone.

## Consequences

**Easier:**

- Minimal code — one callback function, no frontend MFA UI, no session state for "MFA in progress."
- Works immediately in the common dev workflow: start backend in a terminal, see the prompt, type the code.
- `/dev/tty` workaround handles uvicorn stdin redirection better than `input()` alone.
- Token persistence means MFA is a rare event, not a daily friction point.

**Harder:**

- **Cannot authenticate headlessly** — CI uses mocked Garmin clients (`GARMIN_EMAIL` / `GARMIN_PASSWORD` test values in CI env); real auth is never exercised in GitHub Actions.
- Deploying to a remote server breaks this flow entirely — there is no terminal attached to the process.
- MFA timeout or wrong code leaves the server in a 503 state until manual retry; no in-app feedback beyond checking `/api/auth/status`.
- If the backend is started detached from a terminal (systemd, Docker without `-t`), the MFA prompt may be invisible.

**Risks accepted:**

- Deployment is blocked on implementing a non-terminal MFA path — consciously accepted while the app remains local-only.
- MFA codes typed in a terminal are not logged by our code, but could appear in shell history or terminal scrollback — acceptable for personal local use.
