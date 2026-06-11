from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.integrations.keycloak_client import KeycloakClient

security = HTTPBearer()
_keycloak = KeycloakClient()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Valida o JWT e retorna o usuário autenticado com sub, email e roles."""
    payload = _keycloak.validate_token(credentials)
    roles = _keycloak.extract_roles(payload)
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email") or payload.get("preferred_username"),
        "roles": roles,
    }


def require_manager(current_user: dict = Depends(get_current_user)) -> dict:
    """Permite acesso somente a usuários com role MANAGER."""
    if "MANAGER" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: papel MANAGER necessário",
        )
    return current_user


def require_self_or_manager(
    user_id: str, 
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Permite acesso a MANAGER irrestritamente.
    Para PARTICIPANT, a validação de 'self' é feita pela camada de serviço,
    que compara o e-mail do token com o e-mail do usuário alvo no banco.
    Esta dependência apenas garante que o usuário está autenticado.

    Nota: o 'sub' do JWT é o UUID do Keycloak, diferente do ID de domínio
    (usr_xxx). Por isso a comparação de 'self' é feita por e-mail no service.
    """
    if "MANAGER" not in current_user.get("roles", []) and not current_user.get("email"):
        raise HTTPException(status_code=401, detail="Token sem identidade de usuário")
    return current_user
