# Epic-01 Skeleton Design

## Problem Statement
Every later Epic-01 story (and every other epic) needs a running service that knows who the caller is and
what role they have. Nothing exists yet — no project, no app, no schema.

## Proposed Solution
A walking skeleton: thinnest end-to-end slice (login → token → authenticated `/me` → role gate) on the final
stack and final layering, so further stories add code without restructuring.

Approaches considered:
1. **Hand-rolled on spec libraries (chosen)** — `pyjwt`, `argon2-cffi`, `pydantic-settings`. Full control over
   claims (`act`, `trainer_id`), constant-time failure path and the error contract.
2. `fastapi-users` — fast start, but fights the spec's roles/tenancy/impersonation model and error shape.
3. External IdP (Keycloak/Auth0) — out of the spec's stack; overkill for the MVP.

## Architecture
`api/v1/<domain>/routes.py` → `services/` → `repositories/` → `models/` (Conventions §2).
`core/` holds config, security (hash + JWT), errors; `api/deps.py` holds `get_session`, `current_principal`,
`require_role`. Services depend on a repository **Protocol**, so unit tests swap a fake.

## Data Model
`users` only (Epic-01 §7): UUID PK, `email` citext unique, `password_hash`, `role` enum, `status` enum,
flags, timestamps. Created by one Alembic migration. `Principal` is a frozen dataclass, not an ORM object.

## API Design
- `POST /api/v1/auth/login` `{email, password}` → `200 {access_token, token_type}`
- `GET /api/v1/me` → `200 {id, email, role, status}`

## Error Handling
Domain exceptions (`AppError` → `UnauthenticatedError` 401, `PermissionDeniedError` 403, `NotFoundError` 404,
`ConflictError` 409) mapped by one handler to `{"error": {code, message, details}}`. Validation errors use the
same shape with 422.

## Testing Strategy
Unit tests on `AuthService` with a fake repository; e2e via `httpx.AsyncClient` + ASGI transport with the
repository dependency overridden. No Postgres in the test run (user decision).

## Security Considerations
argon2id with spec parameters; dummy verify for unknown emails; identical 401 for every login failure;
status re-read per request; JWT secret from env, never committed; request models `extra="forbid"`.

## Open Questions
- Refresh tokens, rate limiting, tenancy — deferred beyond the skeleton.
