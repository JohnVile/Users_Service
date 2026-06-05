from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_manager
from app.schemas.user_schema import UserCreate, UserPage, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", status_code=201, response_model=UserResponse)
def cria_usuario(data: UserCreate, db: Session = Depends(get_db)):
    service = UserService()
    return service.criacao_de_usuario(db, data)


@router.get("/", response_model=UserPage)
def lista_usuarios(
    status: Optional[Literal["ACTIVE", "INACTIVE"]] = Query(None),
    role: Optional[Literal["MANAGER", "PARTICIPANT"]] = Query(None),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user=Depends(require_manager),
):
    service = UserService()
    return service.lista_de_usuarios(
        db, status=status, role=role, page=page, size=size
    )


# Other routes (to be implemented):
# @router.get("/{user_id}")
# @router.patch("/{user_id}")
# @router.delete("/{user_id}")
# @router.put("/{user_id}/roles")
