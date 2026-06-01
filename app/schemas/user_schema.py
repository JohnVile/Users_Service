from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=3)
    email: EmailStr
    roles: Optional[List[str]] = ["PARTICIPANT"]


class UserUpdate(BaseModel):
    name: Optional[str] = None


class RoleUpdate(BaseModel):
    roles: List[str]


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    status: str
    roles: List[str]
    created_at: datetime

    @field_validator("roles", mode="before")
    @classmethod
    def parse_roles(cls, v):
        if isinstance(v, str):
            return [r.strip() for r in v.split(",")]
        return v

    class Config:
        from_attributes = True