from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserAccounts(BaseModel):
    id: UUID
    full_name: str | None
    email: str
    hashed_password: str
    is_active: bool
    is_superuser: bool = False
    role: str
    created_at: datetime
    updated_at: datetime


class UserRoleUpdate(BaseModel):
    role: str