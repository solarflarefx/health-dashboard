# ADR-005: Branch Strategy, CI, and Automated PR Review

## Status

Accepted

## Date

2026-04-29 (CodeRabbit); 2026-06-11 (GitHub Actions CI merged)

## Context

As the project grew from a solo prototype (placeholder dashboard, April 2026) to a working Garmin integration with tests on both sides, we needed guardrails before merging changes to `main`:

- Backend pytest suite (62+ tests covering config, models, endpoints).
- Frontend Jest tests (MetricCard, SectionPanel, and related components).
- Consistent review quality without relying solely on self-review.

The repo is a personal project on GitHub, developed primarily by one contributor using feature branches and pull requests.

## Decision

**Branch and merge workflow**

- `main` is the protected default branch.
- All changes go through **feature branches + pull requests** (evidenced by PRs #1–#4 in git history).
- **Linear history** — merge commits are avoided in favor of squash/rebase merges that keep `main` readable.
- **Required status checks** must pass before merge (CI workflow on `pull_request`).
- **Conversation resolution** required on PR review threads before merge.

**GitHub Actions CI** (`.github/workflows/ci.yml`)

Triggers on `push`, `pull_request` to `main`, and `workflow_dispatch`. Two jobs run **in parallel**:

| Job | Runner | Steps |
|---|---|---|
| `backend-tests` | `ubuntu-latest` | `setup-uv` (Python 3.12) → `uv sync --frozen` → `uv run pytest tests/ -v` |
| `frontend-tests` | `ubuntu-latest` | `setup-node` (Node 22) → `npm ci` → `npm test -- --watchAll=false` |

Additional CI hardening added during PR #3 review:

- Actions pinned to commit SHAs (supply-chain safety).
- `concurrency` group with `cancel-in-progress: true` to avoid duplicate runs.
- Minimal `permissions: contents: read` and `persist-credentials: false` on checkout.

Backend CI sets dummy `GARMIN_EMAIL` / `GARMIN_PASSWORD` env vars — tests mock the Garmin client and never hit the real API.

**CodeRabbit for automated PR review**

- Configured via `.coderabbit.yaml` at the repo root.
- `profile: assertive`, English, with path-specific instructions for `backend/**/*.py`, `**/*.tsx`, and `backend/tests/**`.
- Added in PR #1 (`chore/add-coderabbit-config`, merged 2026-04-29).

**Repo visibility trade-off**

CodeRabbit's full Pro features (assertive review profile, path instructions, review status) are available on public repositories at no cost. The repo was made **public** to access those features rather than paying for a private-repo plan — acceptable because the codebase contains no credentials (`.env`, `.secrets/` are git-ignored) and holds only personal project code, not proprietary business logic.

## Alternatives Considered

**Push directly to `main` without PRs.**

Used informally in the earliest commits, but abandoned once tests and CodeRabbit were in place. Direct pushes skip review and CI gating.

**Single CI job running both test suites sequentially.**

Rejected — backend and frontend have independent dependency trees; parallel jobs finish faster and isolate failures.

**GitLab CI, CircleCI, or pre-commit hooks only.**

Rejected — GitHub Actions is native to the hosting platform, free for this repo size, and integrates with branch protection status checks.

**Manual code review only (no CodeRabbit).**

Rejected for a solo project — automated review catches patterns (null handling, async misuse, credential leaks) that are easy to miss when you are the only reviewer. The null-value frontend fixes in PR #2 were partly motivated by review feedback.

**Keep the repo private and pay for CodeRabbit Pro.**

Rejected — making the repo public is free and sufficient given no secrets in source. Revisit if the project ever contains data or code that cannot be public.

**Trunk-based development with feature flags.**

Overkill for a personal dashboard with no production users.

## Consequences

**Easier:**

- Every PR gets automated test results and a CodeRabbit review before merge.
- Parallel CI keeps feedback time reasonable (~2–3 minutes).
- Pinned action SHAs reduce supply-chain risk.
- Public repo makes the project shareable and lets others learn from the ADRs and architecture docs.

**Harder:**

- PR overhead for small one-line fixes — acceptable trade-off for habit-building and CI validation.
- CodeRabbit reviews can be noisy or miss context; assertive profile sometimes flags intentional patterns.
- Public repo means all code and commit history are visible — must stay disciplined about never committing `.env`, tokens, or health data.
- CI does not test real Garmin authentication (mocked) — auth breakage from library or Garmin changes will not be caught automatically.

**Risks accepted:**

- Public visibility of a personal health dashboard codebase — mitigated by gitignore rules and architecture doc guidance to never paste credentials or health data into issues or commits.
- Dependency on GitHub Actions and CodeRabbit as external services — acceptable for a personal project; no self-hosted fallback.
