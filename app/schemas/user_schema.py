from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=3)
    email: EmailStr
    roles: Optional[List[str]] = ["PARTICIPANT"]


class UserUpdate(BaseModel):
    name: Optional[str] = None


class RoleUpdate(BaseModel):
    roles: List[str]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    email: EmailStr
    status: str
    roles: List[str]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(
        default=None, serialization_alias="updatedAt"
    )
    deactivated_at: Optional[datetime] = Field(
        default=None, serialization_alias="deactivatedAt"
    )

    @field_validator("roles", mode="before")
    @classmethod
    def parse_roles(cls, v):
        if isinstance(v, str):
            return [r.strip() for r in v.split(",") if r.strip()]
        return v


class PageMetadata(BaseModel):
    page: int
    size: int
    totalElements: int
    totalPages: int


class UserPage(BaseModel):
    items: List[UserResponse]
    page: PageMetadata
