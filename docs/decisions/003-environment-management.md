# ADR-003: Environment and Secret Management

## Status

Accepted

## Date

2026-04-08

## Context

The split-stack architecture (ADR-001) means two runtimes with different configuration needs:

- The **frontend** only needs the backend API URL — a value safe to embed in the client bundle via `NEXT_PUBLIC_*`.
- The **backend** holds Garmin email/password and manages session tokens written to disk after login.

Early development hit a practical bug: token files were resolved relative to the **current working directory** rather than the project root. Starting `uvicorn` from `backend/` vs. the repo root wrote tokens to different paths, causing confusing re-auth loops and "missing token" behavior.

Constraints:

- No secrets in git — Garmin credentials and session tokens are personal and must stay local.
- Python dependency management should be fast and reproducible for CI.
- Configuration should be validated at startup, not discovered as `KeyError` mid-request.

## Decision

**Python package management: `uv`**

- Backend dependencies declared in `backend/pyproject.toml`, lockfile in `backend/uv.lock`.
- CI installs via `astral-sh/setup-uv` with `uv sync --frozen` (see `.github/workflows/ci.yml`).
- Dev dependencies (pytest, httpx) in `[dependency-groups] dev`.
- Project convention: always `uv add <package>`, never `pip install` or manual `pyproject.toml` edits.

**Separated environment files**

| File | Consumer | Contents |
|---|---|---|
| `.env.local` (git-ignored) | Next.js | `NEXT_PUBLIC_API_URL` only |
| `backend/.env` (git-ignored) | FastAPI via `pydantic-settings` | `GARMIN_EMAIL`, `GARMIN_PASSWORD` |
| `.env.example` (committed) | Documentation | Template for both, no real values |

`backend/app/config.py` loads `backend/.env` via `SettingsConfigDict(env_file=...)`. The frontend reads `process.env.NEXT_PUBLIC_API_URL` in `lib/api.ts`.

**Token store: project-root-relative path via `pathlib`**

```python
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
TOKEN_STORE_PATH: Path = _PROJECT_ROOT / ".secrets" / "garmin"
```

- `config.py` lives at `backend/app/config.py` → three `.parent` hops reach the repo root.
- Tokens are written to `<project_root>/.secrets/garmin/garmin_tokens.json` regardless of where `uvicorn` is launched from.
- `.secrets/` and `backend/.env` are git-ignored (`.gitignore` lines 119–124).
- `garmin_client.py` calls `TOKEN_STORE_PATH.mkdir(parents=True, exist_ok=True)` before login.

## Alternatives Considered

**`pip` + `requirements.txt` or Poetry.**

Rejected in favor of `uv` — faster installs, built-in lockfile, and native `pyproject.toml` support without Poetry's extra abstraction. `uv` was adopted from the first backend commit.

**Single root `.env` for both frontend and backend.**

Rejected — Next.js only exposes `NEXT_PUBLIC_*` vars to the browser; mixing Garmin credentials in the same file increases the risk of accidental exposure and blurs the security boundary between client-safe and server-only config.

**Token store relative to `backend/` or configurable via env var.**

Rejected after hitting cwd bugs — a fixed project-root path is predictable and matches where `.gitignore` already excludes `.secrets/`. An env var override adds configuration surface for no benefit in a single-developer project.

**Docker secrets or a cloud secret manager.**

Deferred — unnecessary for local-only development; revisit if we deploy beyond localhost.

## Consequences

**Easier:**

- Clear security boundary: frontend env has no secrets; backend env has credentials; token files are a third, git-ignored category.
- `pydantic-settings` fails fast at import time if `GARMIN_EMAIL` or `GARMIN_PASSWORD` are missing.
- `uv sync --frozen` gives reproducible CI builds matching local dev.
- Token path is stable no matter which directory you `cd` into before starting the server.

**Harder:**

- New developers must copy `.env.example` to **two** files (`.env.local` and `backend/.env`) — easy to miss one.
- `uv` is newer than pip/Poetry; fewer Stack Overflow answers, though Astral's docs are good.
- Token files on disk are a local secret — no rotation policy, no encryption at rest.

**Risks accepted:**

- Plain-text credentials in `backend/.env` and plain-text tokens in `.secrets/garmin/` — acceptable on a trusted local machine, not for shared or deployed environments without additional hardening.
- If `_PROJECT_ROOT` resolution breaks (e.g. backend moved outside the monorepo), token paths break silently — mitigated by tests in `backend/tests/test_config.py`.
