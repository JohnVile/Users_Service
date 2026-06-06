from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_manager, require_self_or_manager
from app.schemas.user_schema import (
    DeactivateRequest,
    RoleUpdate,
    UserCreate,
    UserPage,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", status_code=201, response_model=UserResponse)
def cria_usuario(data: UserCreate, db: Session = Depends(get_db)):
    """Cria usuário no domínio e no Keycloak. Endpoint público (sem token)."""
    return UserService().criacao_de_usuario(db, data)


@router.get("/", response_model=UserPage)
def lista_usuarios(
    status: Optional[Literal["ACTIVE", "INACTIVE"]] = Query(None),
    role: Optional[Literal["MANAGER", "PARTICIPANT"]] = Query(None),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_manager),
):
    """Lista usuários com filtros e paginação. Restrito a MANAGER."""
    return UserService().lista_de_usuarios(
        db, status=status, role=role, page=page, size=size
    )


# @router.get("/{user_id}", response_model=UserResponse)

# @router.patch("/{user_id}", response_model=UserResponse)


@router.delete("/{user_id}", response_model=UserResponse)
def desativar_usuario(
    user_id: str,
    data: DeactivateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_self_or_manager),
):
    """Desativa logicamente o usuário e publica evento UserDeactivated. MANAGER pode desativar qualquer um; PARTICIPANT apenas o próprio."""
    return UserService().desativar_usuario(db, user_id, data.reason, current_user)


@router.put("/{user_id}/roles", response_model=UserResponse)
def atualiza_papeis_usuario(
    user_id: str,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager),
):
    """Substitui integralmente os papéis do usuário. Restrito a MANAGER."""
    return UserService().atualiza_papeis_usuario(
        db, user_id, data.roles, current_user
    )
