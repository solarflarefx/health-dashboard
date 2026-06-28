# ADR-006: Serialize Garmin Client Access with a Shared Lock

## Status

Accepted

## Date

2026-06-27

## Context

The Garmin client is a process-wide singleton (`garmin_client.py`) wrapping a `requests.Session` via the `garminconnect` library. `requests.Session` is **not thread-safe** — concurrent calls from multiple threads can corrupt cookies, connection state, or in-flight requests.

The original `services/garmin.py` implementation used `asyncio.gather` with `asyncio.to_thread` in two places:

- **Two-way concurrency** in `fetch_heart_health_metrics` (`get_heart_rates` + `get_stats`) and `fetch_movement_metrics` (`get_activities_by_date` + `get_stats`).
- **Unbounded concurrency** in `_fetch_stats_history`, which issued one `get_stats` call per day in the history window (up to 90 days) via `asyncio.gather`.

`fetch_today_metrics` and `fetch_vo2max_trend` were already sequential (single call or a simple loop), but they still called `client.get_*` directly without synchronization.

`asyncio.gather` remains visible in `fetch_heart_health_metrics` and `fetch_movement_metrics` for combining two independent results in one expression. After this decision, the actual HTTP calls underneath are serialized by the same lock — `gather` there is retained for structuring the await, not for genuine network-level concurrency.

This project has already hit Garmin rate limiting during development (see `garmin_client.py` backoff logic and ADR-002). Issuing many parallel `get_stats` calls for a history batch that will be discarded on the first failure is especially wasteful.

## Decision

**Introduce a single module-level `threading.Lock` (`_client_lock`) wrapped by a `_locked_client_call` helper, used for every `client.get_*` invocation across all service methods.**

```python
_client_lock = threading.Lock()

def _locked_client_call(fn, *args, **kwargs):
    with _client_lock:
        return fn(*args, **kwargs)
```

Every blocking Garmin call follows the pattern:

```python
await asyncio.to_thread(_locked_client_call, client.get_stats, date_str)
```

**Change multi-day history fetches from `asyncio.gather` to a sequential `for` loop** in `_fetch_stats_history`:

- Once the lock serializes HTTP, `gather` provided no real concurrency for history anyway.
- Sequential fetching **fails fast** — the loop stops on the first exception and does not schedule or complete requests for remaining days.
- History date windows are anchored to UTC via `_utc_today()` so the "last N days" range does not shift at local midnight on non-UTC hosts.

`fetch_heart_health_metrics` and `fetch_movement_metrics` keep `asyncio.gather` for readability; `_client_lock` still serializes the underlying calls.

## Alternatives Considered

**Bounded concurrency via a semaphore (e.g. allow 3–5 parallel calls).**

Rejected — adds complexity without removing the underlying single-session thread-safety risk unless every call still holds a global lock. Partial parallelism would also increase 429 exposure.

**Per-method locks instead of one shared lock.**

Rejected — different `client.get_*` methods share the same `requests.Session`. Separate locks would not prevent races between, say, `get_stats` and `get_heart_rates` running concurrently.

**Keep `asyncio.gather` for history once the lock was in place (readability only).**

Rejected — sequential code is simpler to reason about for N-day loops, and `gather`'s apparent concurrency was misleading once calls are serialized underneath. More importantly, `gather` schedules all thread-pool jobs up front, so a failure on day 2 of 30 still queues days 3–30 before the exception propagates.

**Per-request Garmin client instances (no singleton).**

Rejected — each instance would require its own login/token handling, multiplying auth overhead and complicating token persistence (ADR-003). Not justified for a single-user local dashboard.

## Consequences

**Easier:**

- Eliminates an entire class of intermittent, hard-to-reproduce session/cookie corruption bugs from concurrent access to the singleton client.
- Fail-fast history fetches avoid unnecessary Garmin API calls when a batch will be discarded after a partial failure — relevant given prior rate-limit pain.
- One clear rule for contributors: never call `client.*` directly; always go through `_locked_client_call`.

**Harder:**

- Slower for large history ranges — sequential round-trips instead of (illusory) concurrent ones. A 90-day history request is 90 serial HTTP calls.
- No throughput gain from `gather` on heart/movement endpoints; the lock makes them effectively sequential too.

**Risks accepted:**

- Performance is acceptable for a single-user personal dashboard with typical `days=7` defaults and a `days > 30` warning in logs.
- If this app were ever extended to serve **multiple concurrent users**, this design would need revisiting — e.g. a connection pool, per-user client instances, or a queue — which would also require redesigning the singleton in `garmin_client.py`. Out of scope today.

**Documentation:**

- `docs/architecture.md` updated with a "Garmin client access" section and diagrams reflecting the lock and sequential history path.
