from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.keycloack_client import KeycloakClient
from app.repositories.user_repository import UserRepository

security = HTTPBearer()
_keycloak = KeycloakClient()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = _keycloak.validate_token(credentials)
    roles = _keycloak.extract_roles(payload)

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email") or payload.get("preferred_username"),
        "roles": roles,
    }


def require_manager(current_user: dict = Depends(get_current_user)):
    if "MANAGER" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return current_user


def require_self_or_manager(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if "MANAGER" in current_user.get("roles", []):
        return current_user

    user = UserRepository().busca_usuario_por_id(db, user_id)
    if user is None:
        return current_user

    if user.email != current_user.get("email"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    return current_user
