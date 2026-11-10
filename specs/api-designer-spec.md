# API Spec

Base path `/api/v1`. JSON only. Bearer JWT auth (`Authorization: Bearer <token>`). Architecture: `architect-architecture.md`.

## Error envelope (all non-2xx)

```python
class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
```

| Status | code | When |
|--------|------|------|
| 401 | `INVALID_CREDENTIALS` | login: unknown email, wrong password, inactive user (identical body) |
| 401 | `UNAUTHENTICATED` | `/me`: missing, malformed, expired token; user inactive or deleted |
| 403 | `PERMISSION_DENIED` | `require_role` mismatch (no skeleton route uses it yet) |
| 422 | `VALIDATION_ERROR` | request body fails schema; `details` = `[{"field", "message"}]` |

### [TASK-001] POST /auth/login (2026-11-10)

**Domain:** Auth. Tag `auth`, summary "Issue access token", no auth required.

```python
class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
```

**Status codes:** 200 success; 401 `INVALID_CREDENTIALS`; 422 `VALIDATION_ERROR` (includes unknown fields).

```json
// request
{"email": "anna@example.com", "password": "s3cret-pass"}
// 200
{"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer"}
// 401
{"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password", "details": null}}
```

Token: HS256, TTL 15 min, claims `sub`, `role`, `trainer_id`, `act`, `jti`.

### [TASK-001] GET /me (2026-11-10)

**Domain:** Users. Tag `users`, summary "Current caller's account", requires `current_principal`.

```python
class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    role: Role
    status: UserStatus
```

**Status codes:** 200 success; 401 `UNAUTHENTICATED`. `password_hash` and flags are never exposed.

```json
// 200
{"id": "0194f6a2-7c1e-7b3a-9d41-2f6c8a1e5b90", "email": "anna@example.com", "role": "trainer", "status": "active"}
// 401
{"error": {"code": "UNAUTHENTICATED", "message": "Not authenticated", "details": null}}
```

## Handler outline

- `app/api/v1/auth/routes.py`: `login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse`
- `app/api/v1/users/routes.py`: `me(principal: Principal = Depends(current_principal), service: UserService = Depends(get_user_service)) -> MeResponse`
- Both declare `responses={401: {"model": ErrorResponse}}` (login adds 422) so OpenAPI shows the envelope.
