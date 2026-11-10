from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.users.routes import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="Accelerator")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    register_error_handlers(app)
    return app
