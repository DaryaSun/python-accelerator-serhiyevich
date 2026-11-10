# Epic-01 Walking Skeleton Implementation Plan

**Task:** TASK-001

> **For the implementer:** Use `git-worktrees` to create an isolated workspace, then implement with the `coder` skill.

**Goal:** Login -> JWT -> `GET /api/v1/me` -> `require_role`, on the final layering.

**Architecture:** `api -> services -> repositories (Protocol) -> models`, `core` imported by all. Services take a `UserRepository` Protocol; tests use a fake, no Postgres. Errors are domain exceptions mapped by one handler to `{"error": {code, message, details}}`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, pyjwt, argon2-cffi, pydantic-settings, `pydantic[email]`, uuid6, uv, ruff, mypy strict, pytest-asyncio, httpx.

Specs: `specs/architect-architecture.md` (D1-D8), `specs/api-designer-spec.md`. Commit commands are for the user to run.

---

### Task 1: Project scaffold

**Files:** Create `pyproject.toml`, `.env.example`, `app/__init__.py`, `tests/__init__.py`

1. `uv init`; add deps: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pyjwt`, `argon2-cffi`, `pydantic-settings`, `pydantic[email]`, `uuid6`; dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`.
2. Configure ruff, mypy (`strict` on `app/`), pytest (`asyncio_mode = "auto"`).
3. `.env.example`: `APP_DATABASE_URL`, `APP_JWT_SECRET` (placeholder, no real secret).
4. Verify: `uv run ruff check . && uv run mypy app && uv run pytest` (pytest: "no tests ran" is OK).
5. Commit: `git add pyproject.toml uv.lock .env.example app tests && git commit -m "chore: project scaffold"`

### Task 2: core (config, errors, security)

**Files:** Create `app/core/{config,errors,security}.py`; Test `tests/unit/test_security.py`

1. Failing test: hash/verify round-trip; wrong password fails; `decode_token(encode_token(...))` returns claims incl. `sub, role, trainer_id, act, jti`; expired token raises.
2. Verify fails: `uv run pytest tests/unit/test_security.py` -> ImportError.
3. Implement signatures only:
   - `config.py`: `class Settings(BaseSettings)` (D5), `get_settings() -> Settings` (`lru_cache`)
   - `errors.py`: `AppError(code, message, details=None)` with class-level `status_code`; `UnauthenticatedError` 401, `PermissionDeniedError` 403, `NotFoundError` 404, `ConflictError` 409
   - `security.py`: `Role(StrEnum)`, `Principal` (frozen, slots), `hash_password(str) -> str`, `verify_password(hash, str) -> bool`, `DUMMY_HASH`, `encode_token(...) -> str`, `decode_token(token, settings) -> dict`
   - argon2id `time_cost=3, memory_cost=65536, parallelism=4`
4. Verify passes: `uv run pytest tests/unit/test_security.py && uv run mypy app`
5. Commit: `git add app/core tests/unit && git commit -m "feat(core): config, errors, security"`

### Task 3: db and model

**Files:** Create `app/db/{base,session}.py`, `app/models/user.py`

1. `base.py`: `class Base(DeclarativeBase)`.
2. `session.py`: lazy engine/sessionmaker (D6); `async def get_session() -> AsyncIterator[AsyncSession]`.
3. `user.py`: `UserStatus(StrEnum)`; `User` with columns per requirements Models table; UUIDv7 default via `uuid6.uuid7`; `email` citext unique.
4. Verify: `uv run mypy app && uv run python -c "import app.models.user"`
5. Commit: `git add app/db app/models && git commit -m "feat(models): user model"`

### Task 4: Alembic migration (written, not run)

**Files:** Create `alembic.ini`, `app/db/migrations/env.py`, `app/db/migrations/versions/0001_users.py`

1. Async `env.py` reading the URL from `Settings`.
2. `0001_users.py`: `CREATE EXTENSION IF NOT EXISTS citext`, `users` table, role/status enums; `downgrade` drops them.
3. Verify: `uv run ruff check app/db && uv run mypy app` (no DB run, per Gap Analysis).
4. Commit: `git add alembic.ini app/db/migrations && git commit -m "feat(db): users migration"`

### Task 5: Repository + fake

**Files:** Create `app/repositories/user_repo.py`, `tests/fakes.py`

1. `UserRepository(Protocol)`: `async get_by_email(email: str) -> User | None`, `async get_by_id(user_id: UUID) -> User | None`.
2. `SqlUserRepository(session)` implements it (excludes `deleted_at IS NOT NULL`).
3. `FakeUserRepository(users: list[User])` in `tests/fakes.py`.
4. Verify: `uv run mypy app tests/fakes.py`
5. Commit: `git add app/repositories tests/fakes.py && git commit -m "feat(repo): user repository"`

### Task 6: AuthService (TDD)

**Files:** Create `app/services/auth_service.py`; Test `tests/unit/test_auth_service.py`

1. Failing tests with `FakeUserRepository`: success returns token; wrong password -> `UnauthenticatedError("INVALID_CREDENTIALS")`; unknown email -> same error and `verify_password` called with `DUMMY_HASH` (monkeypatch spy); inactive user -> same error.
2. Verify fails: `uv run pytest tests/unit/test_auth_service.py`
3. Implement `AuthService(repo, settings)`, `async login(email: str, password: str) -> str`.
4. Verify passes: `uv run pytest tests/unit && uv run mypy app`
5. Commit: `git add app/services tests/unit && git commit -m "feat(auth): auth service"`

### Task 7: UserService

**Files:** Create `app/services/user_service.py`; Extend `tests/unit/test_auth_service.py` or add `tests/unit/test_user_service.py`

1. Failing test: `get_active` returns active user; inactive/deleted/missing -> `UnauthenticatedError("UNAUTHENTICATED")`.
2. Implement `UserService(repo)`, `async get_active(user_id: UUID) -> User`.
3. Verify: `uv run pytest tests/unit`
4. Commit: `git add app/services tests/unit && git commit -m "feat(users): user service"`

### Task 8: API layer (TDD, e2e)

**Files:** Create `app/api/{deps,errors}.py`, `app/api/v1/auth/{routes,schemas}.py`, `app/api/v1/users/{routes,schemas}.py`, `app/main.py`, `tests/conftest.py`; Test `tests/e2e/test_auth_flow.py`

1. `conftest.py`: `app = create_app()`; override `get_user_repo` -> `FakeUserRepository` and `get_settings`; `client` fixture = `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.
2. Failing e2e tests: login -> `/me` returns `{id, email, role, status}`; bad password -> 401 `INVALID_CREDENTIALS` identical to unknown email; `/me` without token and with expired token -> 401 `UNAUTHENTICATED`; invalid email or extra field on login -> 422 `VALIDATION_ERROR` with `details=[{field, message}]`; `require_role` mismatch -> 403 `PERMISSION_DENIED` (test route registered on the test app only).
3. Verify fails: `uv run pytest tests/e2e`
4. Implement signatures:
   - `schemas.py`: `LoginRequest`, `TokenResponse`, `MeResponse` exactly per API spec
   - `deps.py`: `get_user_repo`, `get_auth_service`, `get_user_service`, `async current_principal(...) -> Principal`, `require_role(*roles: Role)`
   - `errors.py`: `register_error_handlers(app)`; `ErrorResponse`/`ErrorBody` models
   - routes: `login`, `me` with `responses={401: ...}` (login adds 422)
   - `main.py`: `create_app() -> FastAPI`, routers under `/api/v1`
5. Verify passes: `uv run pytest tests/e2e`
6. Commit: `git add app tests && git commit -m "feat(api): login and me endpoints"`

### Task 9: Final gate

1. Run: `uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest`
2. Expected: all clean/pass; no Postgres needed.
3. Run `/verify` against `.claude/DOD.md`.
