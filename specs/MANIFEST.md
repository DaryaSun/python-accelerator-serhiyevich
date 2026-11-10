# Project: Epic-01 Identity Service

Layered FastAPI JSON API. TASK-001 builds the walking skeleton: login, JWT, `/me`, role gate.

## Specs Index

| File | Purpose | Depends On | Last Updated |
|------|---------|------------|--------------|
| architect-architecture.md | System design, components, data flow | - | 2026-11-10 |
| api-designer-spec.md | Endpoints, schemas, authentication | architect-architecture | 2026-11-10 |
| docs-generator-implementation.md | Build process, deployment, tooling | - | - |

## Key Decisions

- Layering: `Task/Epics/00_Backend_Conventions.md` §2 (api → services → repositories → models; all → core)
- Services depend on repository Protocols (fakes in tests, no Postgres in the test run)
- Auth: JWT access token (HS256, 15 min) + argon2id; `Principal` frozen dataclass
- Errors: `core/errors.py` domain exceptions → one handler → `{"error": {code, message, details}}`

## Tech Stack

Python 3.12, uv, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2.0 async (asyncpg), Alembic, PostgreSQL 16, pyjwt, argon2-cffi, uuid6, ruff, mypy, pytest + pytest-asyncio + httpx

---

*This manifest is updated automatically by architect, api-designer, and docs-generator skills.*
*See `../spec-desc.md` for specification structure guidelines.*
