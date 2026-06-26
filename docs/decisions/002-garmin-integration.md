# ADR-002: Garmin Connect via python-garminconnect

## Status

Accepted

## Date

2026-04-08 (initial integration); 2026-04-25 (0.3.2 upgrade and working data pipeline)

## Context

The dashboard's entire value depends on reading personal health data from Garmin Connect: daily stats, heart rates, activities, and VO₂ Max history. We needed a way to authenticate and query that data without building a Garmin API client from scratch.

Constraints:

- This is a **personal, non-commercial** project — one Garmin account, local development, no business entity.
- Garmin's official [Connect Developer Program](https://developer.garmin.com/gc-developer-program/overview/) requires application approval, API key provisioning, and a 1–4 week review cycle. It is aimed at commercial integrations, not a solo developer reading their own metrics.
- The unofficial route must handle Garmin's evolving anti-bot measures, including Cloudflare rate limiting (HTTP 429) on login endpoints.

## Decision

Use **[cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect)** (`garminconnect` on PyPI) as the sole Garmin data source.

- Pinned at `garminconnect>=0.3.2` in `backend/pyproject.toml`, with companion deps `curl-cffi>=0.15.0` and `ua-generator>=2.0.25` that the library's newer auth engine relies on.
- All Garmin calls go through the singleton in `backend/app/garmin_client.py`; business logic and field mapping live in `backend/app/services/garmin.py`.
- Four metrics endpoints (`/api/metrics/today`, `/heart`, `/movement`, `/vo2max`) each call a specific `garminconnect` client method and map raw dict responses into Pydantic models.

## Alternatives Considered

**Garmin Connect Developer Program (official API).**

Rejected — requires business approval and a multi-week wait; OAuth and API surface are designed for third-party apps serving many users, not a personal dashboard reading one account's data. Overkill for this use case.

**Direct HTTP scraping without a library.**

Rejected — Garmin's login flow, token format, and endpoint URLs change without notice. Maintaining this ourselves would be a full-time side project.

**Other unofficial libraries or GarminDB-style export pipelines.**

Not pursued — `garminconnect` is the most actively maintained Python option with community fixes for auth breakage.

## The Messy Part: Library Version Upgrade

Early development used older `garminconnect` releases (0.2.x era). Authentication **failed entirely** — every login attempt returned HTTP 429 from Cloudflare, blocking all progress on real data.

The fix required upgrading to **0.3.2**, which introduced a native auth engine with a 5-strategy login chain (`mobile+cffi`, `mobile+requests`, `widget+cffi`, `portal+cffi`, `portal+requests`). The `widget+cffi` strategy in particular bypasses the rate limiting that blocked the older approach.

Additional fallout from the upgrade:

- **Token format changed** — 0.3.2 uses `di_token` / `di_refresh_token` JSON; old garth-format tokens are incompatible. Stale token files had to be deleted manually before login would fall through to credentials.
- **Field mapping bugs surfaced only with real data** — heart rate, stress score, movement rolling window, and VO₂ Max field paths (`response[0]['generic']['vo2MaxPreciseValue']`) all needed fixes after auth finally worked (commit `eaa186c`, 2026-04-25).
- We still wrap the library's internal 429 handling with outer exponential backoff (60 s base, 3 attempts) in `_login_with_backoff()` for the case where all five strategies are simultaneously rate-limited.

The committed history shows `garminconnect>=0.3.1` in the first backend commit and `>=0.3.2` after the working integration — the 0.2.x pain happened during pre-commit exploration.

## Consequences

**Easier:**

- Full access to Garmin Connect data without official API approval.
- Active community maintenance when Garmin changes their login flow.
- `garminconnect` 0.3.2 handles token restore, proactive refresh, and auto-save when a `tokenstore` path is passed to `login()`.

**Harder:**

- **Unofficial and fragile** — Garmin can break login or change response shapes at any time; we have no SLA or changelog to rely on.
- Tied to Python — reinforces the split-stack decision (ADR-001); no way to call Garmin from the Next.js frontend directly.
- Debugging auth failures requires reading library source and stderr, not official API docs.
- Response field names are inconsistent across endpoints; mapping logic in `services/garmin.py` is brittle and Garmin-specific.

**Risks accepted:**

- Project depends on a third-party library reverse-engineering a consumer web API — acceptable for a personal tool, unacceptable for a product serving other users without a fallback plan.
- Cloudflare 429 can still block login during heavy retry periods; we accept occasional manual retry via `POST /api/auth/retry`.
