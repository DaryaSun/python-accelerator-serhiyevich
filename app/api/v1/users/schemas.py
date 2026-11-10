from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.security import Role
from app.models.user import UserStatus


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: Role
    status: UserStatus
