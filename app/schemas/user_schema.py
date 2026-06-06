from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=3)
    email: EmailStr
    roles: List[Literal["MANAGER", "PARTICIPANT"]] = ["PARTICIPANT"]


class UserUpdate(BaseModel):
    # api-docs exige minLength: 3 para name
    name: Optional[str] = Field(None, min_length=3)


class DeactivateRequest(BaseModel):
    # Corresponde a DeactivateUserRequest do api-docs
    reason: str = Field(min_length=3)


class RoleUpdate(BaseModel):
    roles: List[Literal["MANAGER", "PARTICIPANT"]] = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    email: EmailStr
    status: str
    roles: List[str]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, serialization_alias="updatedAt")
    deactivated_at: Optional[datetime] = Field(default=None, serialization_alias="deactivatedAt")

    @field_validator("roles", mode="before")
    @classmethod
    def parse_roles(cls, v):
        # Converte "MANAGER,PARTICIPANT" (str do banco) -> ["MANAGER", "PARTICIPANT"]
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
