from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserUpdate,
    RoleUpdate
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

# Roteamento para criação de usuário
@router.post("/", status_code=201, response_model=UserResponse)
def cria_usuario(data: UserCreate, db: Session = Depends(get_db)):
    service = UserService()
    return service.criacao_de_usuario(db, data)


# Other routes (to be implemented):
# @router.get("/")
# @router.get("/{user_id}")
# @router.patch("/{user_id}")
# @router.delete("/{user_id}")
# @router.put("/{user_id}/roles")
