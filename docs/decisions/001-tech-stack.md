# ADR-001: Split Frontend/Backend Tech Stack

## Status

Accepted

## Date

2026-04-05 (frontend); 2026-04-08 (backend split formalized)

## Context

We needed a personal health dashboard that pulls data from Garmin Connect and presents it in a readable single-page UI. The project started as a learning exercise as much as a utility — we wanted hands-on experience with both a modern React frontend ecosystem and a Python API layer.

Constraints:

- Garmin integration libraries are Python-first (`garminconnect` is the practical choice for personal use).
- The UI needed responsive layout, charting (VO₂ Max trend), and a polished dark-theme dashboard without building a design system from scratch.
- The app is single-user, local-first development; no multi-tenant or real-time requirements.

The initial commit (`bf513f6`, 2026-04-05) scaffolded the frontend only: Next.js 14 App Router, TypeScript, Tailwind CSS, Chart.js, and placeholder metric data. Three days later (`00c5476`, 2026-04-08) we added the FastAPI backend as a separate service under `backend/`.

## Decision

Use a **split architecture**:

| Layer | Stack |
|---|---|
| Frontend | Next.js 14.2 (`app/` router), React 18, TypeScript 5, Tailwind CSS 3.4 |
| Backend | FastAPI, Python 3.12, Pydantic v2, `pydantic-settings`, `uvicorn` |
| Communication | REST over HTTP; frontend reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) |

The frontend is a server-component-driven dashboard (`app/page.tsx` fetches all metrics in parallel via `lib/api.ts`). The backend exposes typed Pydantic responses under `/api/metrics/*` and `/api/auth/*`, with Garmin-specific logic isolated in `backend/app/services/garmin.py` and `backend/app/garmin_client.py`.

## Alternatives Considered

**Single full-stack framework (Next.js API routes, or a Python monolith with server-rendered templates).**

Rejected because:

- We explicitly wanted to practice both the Node/React and Python/FastAPI ecosystems in one project.
- FastAPI pairs naturally with the Python Garmin library and async patterns (`asyncio.to_thread` for blocking Garmin calls).
- Keeping Garmin credentials and token storage entirely on the backend avoids exposing secrets to the browser bundle.

**Django or Flask instead of FastAPI.**

Rejected — FastAPI's native async support, automatic OpenAPI docs, and Pydantic integration matched the "typed API contract" goal with less boilerplate.

**Remix, SvelteKit, or Vite + React instead of Next.js.**

Rejected — Next.js 14 App Router with server components fit the "fetch on render, minimal client JS" dashboard model, and `create-next-app` gave a fast starting point.

## Consequences

**Easier:**

- Clear separation of concerns: frontend knows only REST endpoints and TypeScript types; backend owns Garmin auth and data normalization.
- Independent test suites — Jest for frontend components, pytest for backend endpoints and services.
- Each service can be developed and restarted independently during local dev (`npm run dev` on port 3000, `uvicorn` on port 8000).
- Python ecosystem access for Garmin integration without awkward Node bindings.

**Harder:**

- Two processes, two dependency managers (`npm` + `uv`), and CORS configuration (`main.py` allows `http://localhost:3000`).
- Cross-cutting changes (new metric) require coordinated edits in Pydantic models, service layer, router, TypeScript types, API helper, and UI — documented in `docs/architecture.md` but still multi-file.
- Deployment is two artifacts unless we later containerize or co-locate behind a reverse proxy.

**Risks accepted:**

- No application-level auth on the API today — acceptable for localhost-only use, but deployment will require TLS and access control.
- Operational overhead of running two services locally is fine for a personal dashboard but would be heavier for a team or production SLA.
