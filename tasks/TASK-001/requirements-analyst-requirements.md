# Epic-01 Skeleton Requirements

## Overview
Minimal walking skeleton of the Epic-01 identity service: a layered FastAPI app that can authenticate a user
and answer "who is the caller and what role do they have". It is the foundation the rest of Epic-01 builds on.

## Source
`Task/Epics/Epic-01_User_Management_Authentication_SPEC.md` (§3, §7 `users`, §8, §10) and
`Task/Epics/00_Backend_Conventions.md` (§1, §2, §4, §5, §8). Scope narrowed by the user to a skeleton.

## Functional Requirements
1. FR-001: `POST /api/v1/auth/login` — email + password → JWT access token
   - Acceptance: `200 {access_token, token_type: "bearer"}`; wrong email or password ⇒ `401 INVALID_CREDENTIALS` (same body)
   - Priority: High
2. FR-002: `GET /api/v1/me` — returns the caller's `{id, email, role, status}`
   - Acceptance: missing/invalid/expired token ⇒ `401 UNAUTHENTICATED`
   - Priority: High
3. FR-003: `current_principal` dependency yields `Principal(user_id, role, trainer_id, act)`
   - Acceptance: status is re-read per request; inactive/deleted user ⇒ `401`
   - Priority: High
4. FR-004: `require_role(*roles)` dependency
   - Acceptance: role not allowed ⇒ `403 PERMISSION_DENIED`
   - Priority: High
5. FR-005: Single error contract `{"error": {code, message, details}}` emitted by one exception handler
   - Priority: High

## Non-Functional Requirements
1. NFR-001: Toolchain — uv, ruff (check + format), mypy strict on `app/`, pytest + pytest-asyncio
   - Metric: all four commands clean
2. NFR-002: Layering per Conventions §2 (routes → services → repositories → models)
   - Metric: no SQL in routes, no HTTP in services
3. NFR-003: Schema managed by Alembic — one initial migration for `users`

## Business Rules
1. BR-001: Passwords hashed with argon2id (`time_cost=3, memory_cost=64 MiB, parallelism=4`)
2. BR-002: Login failure is constant-time — a missing user still runs a dummy hash verification
3. BR-003: Login never reveals whether the email exists
4. BR-004: Access token TTL 15 min, claims `sub`, `role`, `trainer_id`, `act`, `jti`
5. BR-005: Only `active` users may log in or be resolved as principal

## Task Breakdown

### Models
| Model | Properties | Relations |
|-------|------------|-----------|
| User | id (UUID), email (citext, unique), password_hash, role, status, is_email_verified, must_change_password, last_login_at, deleted_at, created_at, updated_at | — (profiles out of scope) |

### Services
| Service | Purpose | Methods |
|---------|---------|---------|
| AuthService | Credential check, token issue | `login(email, password)` |
| UserService | Read caller | `get_active(user_id)` |

### Endpoints
| Resource | Endpoints | Purpose |
|----------|-----------|---------|
| auth | `POST /api/v1/auth/login` | Issue access token |
| me | `GET /api/v1/me` | Caller's own account |

### Testing
- Unit: AuthService (success, wrong password, unknown email runs dummy verify, inactive user) with a fake repository
- E2E: login → `/me` flow; `/me` without token ⇒ 401; `require_role` ⇒ 403
- No Postgres in tests (user decision): repositories faked via Protocol, DB session overridden in e2e

## Gap Analysis
- [ ] Out of scope for the skeleton: refresh/logout, password reset, email verification, rate limiting, profiles,
      ShareLinks, tenancy tables, impersonation, GDPR erasure, jobs, load tests
- [ ] Integration tests against real Postgres deferred — migration is written but not exercised in CI
- [ ] Q-01.05 (email verification gate) irrelevant until verification exists
