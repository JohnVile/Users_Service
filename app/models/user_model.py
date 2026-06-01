import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


def gerar_id():
    return f"usr_{uuid.uuid4().hex[:12]}"


class User(Base):

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gerar_id, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    roles = Column(String, nullable=False, default="PARTICIPANT")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deactivated_at = Column(DateTime(timezone=True), nullable=True)