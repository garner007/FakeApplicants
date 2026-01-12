# CLAUDE.md — Applicant Validator (FastAPI + Next.js) Production/TDD Rules

Claude: follow this file **strictly**. This repo must remain **always shippable**: small changes, TDD-first, verified continuously, production-ready code only.

Stack:
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, async SQLAlchemy/asyncpg, Alembic, httpx, structlog
- **Frontend**: React + Next.js, TypeScript, ESLint, Jest + Testing Library, Tailwind

Quality gates (do not weaken):
- **mypy strict = true**
- **ruff** lint rules as configured
- **coverage fail_under = 90%**

---

## Non-negotiables

### TDD every behavior change
For any feature/bugfix:
1) **Write/update a test first** (it must fail for the right reason)
2) Implement the **minimum** to pass
3) Refactor for clarity (tests stay green)
4) Run **tests + lint + typecheck** for the touched area
5) Only then move to the next small slice

Allowed exceptions (explicit, rare):
- Docs-only
- Pure refactor with **no behavior change** (still run tests/lint/typecheck)
- Build/tooling changes (still lint/typecheck; run relevant tests)

### Code must be concise, readable, atomic
- Prefer **simple and obvious** over clever
- Avoid deep nesting, multi-purpose functions, and complicated routines
- One responsibility per function/class/module; one reason to change
- If a function is hard to explain in one sentence, **split it**
- Strong names > comments (comments explain “why”, not “what”)
- Refactoring is part of TDD: after tests pass, **simplify, rename, extract, delete duplication**
- No speculative abstractions (“future-proofing”)

### Never
- Don’t add code without tests (unless exception above)
- Don’t disable or bypass lint/type checks to “make it pass”
- Don’t lower coverage thresholds or relax mypy strictness/ruff rules
- Don’t mix unrelated changes in the same PR
- Don’t log secrets/PII or leak internals in API errors

---

## Definition of Done

A change is “done” only when:
- ✅ Tests updated/added (unit + integration/e2e where appropriate)
- ✅ Lint + format pass
- ✅ Type-check passes
- ✅ Coverage stays **>= 90%**
- ✅ Logging is structured; no secrets/PII
- ✅ Inputs validated at boundaries; errors mapped to correct HTTP responses
- ✅ UI has loading/error/empty states where applicable

---

## Canonical verification commands

### Backend (Python) — from pyproject.toml
Install (typical):
- `pip install -e ".[dev]"`

Fast inner loop (after each meaningful change):
- `pytest -q`
- `ruff check .`
- `mypy src`

Before marking done:
- `ruff format .`
- `ruff check .`
- `mypy src`
- `pytest -q --cov --cov-report=term-missing`

Testing rules:
- Never hit real external services in tests.
- Use `respx` to mock httpx and assert request shape + failure modes (429/5xx/etc).
- Use markers:
  - Integration: `pytest -q -m integration`
  - Skip integration: `pytest -q -m "not integration"`

### Frontend (Next.js) — from package.json
Fast inner loop (after each meaningful change):
- `npm run test`
- `npm run lint`

Before marking done:
- `npm run lint`
- `npm run test`
- `npm run test:coverage`
- `npm run build` (ensures Next build is healthy)

Notes:
- Tests: Jest + Testing Library (`jsdom`)
- Lint: ESLint (`npm run lint`)
- TypeScript: ensure `next build` passes (Next runs TS checks by default in standard setups). Do not bypass TS errors.

---

## Code standards

### Backend (FastAPI)
- Route handlers: validate input → call service/domain layer → translate errors to HTTP responses
- Keep business logic out of routes; isolate I/O at edges
- Keep types explicit; public functions typed
- Error handling:
  - auth: 401/403
  - not found: 404
  - upstream failures: 502/503 as appropriate
  - never leak stack traces or sensitive details

### Database & migrations
- Schema changes require Alembic migrations
- Migrations must be production-safe and preferably reversible
- Add tests for constraints and key queries when changed

### Logging & security
- Use structlog, stable event names + structured fields
- Never log: tokens, passwords, secrets, full PII payloads
- Validate/normalize untrusted input (email/phone/location)
- No raw SQL concatenation; use ORM/parameterized queries
- New env vars must be documented (`.env.example` + README) with safe defaults or fail fast

### Frontend (React/Next.js)
- Keep components small and focused; avoid unnecessary client state
- Handle loading/error/empty states
- Accessibility basics required (labels, semantic HTML, keyboard nav)
- Avoid bundle bloat; don’t add large deps for small needs

---

## Work style (how Claude edits)

- Make **small, reviewable** changes; one concern per PR.
- Follow existing patterns in the repo; don’t invent new architecture.
- If uncertain about conventions, inspect nearby code and follow precedent.
- If Claude slips (missed test/lint/typecheck, or produced complex code), add a short rule here to prevent recurrence.

---

## Commit message format
Use conventional commits:
- feat: new feature
- fix: bug fix
- docs: documentation only changes
- style: formatting, missing semi colons, etc; no code change
- refactor: code change that neither fixes a bug nor adds a feature
- test: adding missing tests or correcting existing tests
- chore: changes to the build process or auxiliary tools and libraries such as documentation generation
- perf: code change that improves performance
- commits should never be attributed to AI - non-negotiable
