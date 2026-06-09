from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.integrations.keycloack_client import KeycloakClient

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


def require_self_or_manager(user_id: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        if "MANAGER" in current_user.get("roles", []):
            return current_user
        if current_user.get("sub") != user_id:
            raise HTTPException(status_code=403, detail="Acesso negado")
        return current_user

    return dependency
