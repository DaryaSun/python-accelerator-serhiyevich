# Architecture

Layered FastAPI service per `Task/Epics/00_Backend_Conventions.md` §2. This file records decisions only;
stack, layering rules, auth and API conventions are not repeated here.

### [TASK-001] Epic-01 Walking Skeleton (2026-11-10)

**Scope:** login → JWT → `GET /api/v1/me` → `require_role`. Design: `tasks/TASK-001/brainstorm-design.md`.

**Files**

| Path | Contents |
|------|----------|
| `pyproject.toml`, `uv.lock`, `alembic.ini`, `.env.example` | deps, ruff, mypy strict on `app/`, pytest-asyncio; env template (no secrets) |
| `app/main.py` | `create_app()`: include routers under `/api/v1`, register error handlers |
| `app/core/config.py` | `Settings(BaseSettings)`, `get_settings()` (`lru_cache`) |
| `app/core/errors.py` | `AppError(code, message, details)` + `UnauthenticatedError`, `PermissionDeniedError`, `NotFoundError`, `ConflictError` |
| `app/core/security.py` | `Role` StrEnum, `Principal`, argon2id hash/verify + dummy hash, JWT encode/decode |
| `app/db/base.py`, `app/db/session.py` | `DeclarativeBase`; async engine + `async_sessionmaker` from settings |
| `app/db/migrations/env.py`, `versions/0001_users.py` | Alembic env; `CREATE EXTENSION citext` + `users` table |
| `app/models/user.py` | `User`, `UserStatus` StrEnum |
| `app/repositories/user_repo.py` | `UserRepository` Protocol + `SqlUserRepository(session)` |
| `app/services/auth_service.py` | `AuthService.login(email, password) -> str` |
| `app/services/user_service.py` | `UserService.get_active(user_id) -> User` |
| `app/api/deps.py` | `get_session`, `get_user_repo`, `get_*_service`, `current_principal`, `require_role(*roles)` |
| `app/api/errors.py` | exception handlers: `AppError`, `RequestValidationError` → error envelope |
| `app/api/v1/auth/{routes,schemas}.py` | `POST /auth/login`; `LoginRequest`, `TokenResponse` |
| `app/api/v1/users/{routes,schemas}.py` | `GET /me`; `MeResponse` |
| `tests/fakes.py`, `tests/conftest.py` | `FakeUserRepository`; app + `AsyncClient(ASGITransport)` fixtures |
| `tests/unit/test_auth_service.py`, `tests/e2e/test_auth_flow.py` | per requirements §Testing |

**Dependency direction** (imports only point down/right; `core` imports nothing from `app`):

```
api (routes, schemas, deps, errors) → services → repositories (Protocol) → models → db.base
                         all layers → core
```

**Key decisions**

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Services take a `UserRepository` **Protocol** (`get_by_email`, `get_by_id`), never a session. `SqlUserRepository` satisfies it structurally. | Unit tests pass `FakeUserRepository`; e2e overrides only `get_user_repo`, which also drops `get_session` from the graph, so no Postgres is touched. |
| D2 | `Principal` = `@dataclass(frozen=True, slots=True)` `(user_id: UUID, role: Role, trainer_id: UUID \| None, act: UUID \| None)` in `core/security.py`. | Immutable, ORM-free value that services can accept later for object-level checks without importing `api`. `Role` lives in `core` so `models` and `Principal` share it without a reverse import. |
| D3 | `current_principal`: `HTTPBearer(auto_error=False)` → `decode_token` → `UserService.get_active(sub)`; any failure raises `UnauthenticatedError`. `require_role(*roles)` returns a dependency raising `PermissionDeniedError`. | Status re-read per request (FR-003); auth is a dependency, never an `if` in a handler (§4). |
| D4 | Exceptions are defined in `core/errors.py` with a class-level `status_code`; the handler is in `api/errors.py`. One function builds `{"error": {code, message, details}}`; `RequestValidationError` → 422 `VALIDATION_ERROR`. | Services raise domain errors without knowing HTTP. Status lives on the class, so a new error needs no edit to the handler. `UnauthenticatedError`→401 extends the §5 table. |
| D5 | `Settings`: `database_url`, `jwt_secret: SecretStr` (min length 32), `jwt_algorithm="HS256"`, `access_token_ttl=timedelta(minutes=15)`; `env_prefix="APP_"`, `.env` optional. Injected via `Depends(get_settings)`, not imported as a global. | Fails fast if the secret is missing; tests override the settings dependency. |
| D6 | Engine/sessionmaker are created lazily on first `get_session`, not at import. | Importing `app.main` in tests needs no DB driver or URL. |
| D7 | Skeleton is read-only (no `last_login_at` write), so no transaction code. The first write story adds a commit/unit-of-work method to the Protocol; the service still owns the transaction (§2). | Smallest skeleton; leaves the transaction pattern open without guessing. |
| D8 | UUIDv7 PKs via `uuid6.uuid7` as the ORM default (Python 3.12 has no `uuid.uuid7`). | §5 requires UUIDv7. |

**Security:** argon2id parameters from BR-001; the dummy hash is computed once at import and verified for unknown emails (BR-002);
every login failure raises the same `UnauthenticatedError("INVALID_CREDENTIALS")`; inactive users get 401 at login and on `/me`;
request schemas use `extra="forbid"`; `password_hash` is never in a response schema.

**Scalability:** stateless JWT, horizontally scalable; `users.email` unique index covers the login lookup.
Deferred: Redis rate limiting, refresh tokens, tenancy (see requirements Gap Analysis).
