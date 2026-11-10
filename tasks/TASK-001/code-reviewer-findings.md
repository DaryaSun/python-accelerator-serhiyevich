# Code Review — TASK-001 Epic-01 Walking Skeleton

Scope: `app/`, `tests/`, `pyproject.toml`. Reference: `specs/architect-architecture.md`, `specs/api-designer-spec.md`,
Epic-01 §7 `users`, §10 Authentication, Conventions §2/§4/§5.

## Summary

Solid skeleton: layering matches D1–D8, no SQL in routes, no HTTP in services, constant-time login and
uniform `INVALID_CREDENTIALS` are correct. No critical issues. Main gaps: the error envelope is not emitted
for framework/unhandled errors, the ORM model drifts from the migration, and `/me` loads the user twice.

Counts: Critical 0 · Major 3 · Minor 6

## Issues Found

### Critical (Must Fix)
- none

### Major (Should Fix)
- [ ] **[bug] [in scope] [medium]** `app/api/errors.py:28` — envelope is not universal. Probed: unknown route → `404 {"detail":"Not Found"}`,
      wrong method → `405 {"detail":...}`, any unhandled exception (e.g. DB down) → plain-text 500. Violates API spec "Error envelope (all non-2xx)" and FR-005.
      **Fix:** add handlers for `starlette.exceptions.HTTPException` (map status → code, e.g. `NOT_FOUND`, `METHOD_NOT_ALLOWED`) and `Exception` → 500 `INTERNAL_ERROR`, both via `_response`. → fix now
- [ ] **[bug] [in scope] [medium]** `app/models/user.py:21` — `ix_users_role_status` exists only in `0001_users.py:40`; the model has no `__table_args__`.
      The next `alembic revision --autogenerate` will emit `drop_index("ix_users_role_status")`.
      **Fix:** `__table_args__ = (Index("ix_users_role_status", "role", "status"),)` on `User`. → fix now
- [ ] **[risk] [in scope] [low]** `app/api/v1/users/routes.py:23` + `app/api/deps.py:47` — `/me` runs `get_active` twice (once in `current_principal`, once in the route): 2 identical queries per request.
      **Fix:** add a `current_user` dependency returning `User` (calls `get_active` once), build `current_principal` on top of it; FastAPI caches it per request, so `/me` depends on `current_user` with no second query. → fix now

### Minor (Consider)
- [ ] **[risk] [in scope] [low]** `app/api/deps.py:48` — `Principal(user.id, user.role, None, None)` discards the token's `trainer_id`/`act` claims, though FR-003/D3 say the principal carries them. Once impersonation lands, `act` is silently lost (audit gap, Conventions §4).
      **Fix:** parse `trainer_id`/`act` from claims (UUID or None, invalid → 401). → fix now or record as explicit deferral in the plan
- [ ] **[risk] [in scope] [low]** `app/core/errors.py:16` / `app/api/errors.py:24` — 401 responses carry no `WWW-Authenticate: Bearer` header (RFC 6750; probed: header absent).
      **Fix:** give `AppError` an optional `headers` attribute, set it on `UnauthenticatedError`, pass it to `JSONResponse`. → fix now
- [ ] **[bug] [in scope] [low]** `app/api/errors.py:36` — `loc[1:]` yields meaningless `field` values: missing body → `""`, malformed JSON → `"1"` (probed).
      **Fix:** for single-segment `loc` or `json_invalid` type use `"body"`; otherwise keep `loc[1:]`. → fix now
- [ ] **[risk] [in scope] [low]** `app/api/v1/users/schemas.py:13` — `MeResponse.email: EmailStr` re-validates stored data on output; a stored `x@corp.local` raises `ValidationError` → 500 (probed).
      **Fix:** `email: str` in response models; validate only on input. → fix now
- [ ] **[risk] [in scope] [low]** `tests/conftest.py:20`, `tests/unit/test_auth_service.py:17`, `tests/unit/test_security.py:19` — `mypy app tests` fails with 3 `unused-ignore` errors; the two unit-file `settings` fixtures duplicate the conftest one.
      **Fix:** drop the `# type: ignore[arg-type]` comments and delete the duplicate fixtures. → fix now
- [ ] **[risk] [in scope] [low]** `tests/e2e/test_auth_flow.py:43` — `current_principal` branches untested over HTTP: token of an inactive/deleted user (FR-003 per-request re-read; `off@example.com` fixture is unused), tampered signature, non-UUID `sub` (`deps.py:45`).
      **Fix:** parametrize `test_me_without_token` over these tokens, all expecting `401 UNAUTHENTICATED`. → fix now

### Positive Notes
- Clean layering per D1–D4: `UserRepository` Protocol, services raise domain errors, status code lives on the error class.
- Login: dummy-hash verify for unknown/deleted users, single failure code incl. inactive users, `extra="forbid"`, `password_hash` never exposed.
- `jwt_secret: SecretStr` with min length enforced (verified: short secret rejected); lazy engine (D6); UUIDv7 default (D8).
- Tests use the fake repository and override only `get_user_repo`/`get_settings` — no DB needed.

## Verification Evidence

| Check | Result |
|-------|--------|
| `uv run pytest -q` | 17 passed |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 40 files already formatted |
| `uv run mypy app` | Success, 28 files |
| `uv run mypy app tests` | 3 errors (`unused-ignore`, see Minor) |
| Probes (404/405/422/401 headers, `.local` email) | behaviour as described above |
