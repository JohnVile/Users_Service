import requests

from jose import jwt, JWTError
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings


class KeycloakClient:

    def __init__(self):
        self.server_url = settings.KEYCLOAK_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET

    # =========================================================
    # URLS
    # =========================================================

    @property
    def admin_token_url(self):
        # Token de admin vem do realm master via admin-cli
        return f"{self.server_url}/realms/master/protocol/openid-connect/token"

    @property
    def users_url(self):
        return f"{self.server_url}/admin/realms/{self.realm}/users"

    @property
    def certs_url(self):
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/certs"

    # =========================================================
    # ADMIN TOKEN
    # =========================================================

    def get_admin_token(self):
        data = {
            "client_id": "admin-cli",
            "username": settings.KEYCLOAK_ADMIN_USER,
            "password": settings.KEYCLOAK_ADMIN_PASSWORD,
            "grant_type": "password"
        }

        response = requests.post(self.admin_token_url, data=data)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao autenticar no Keycloak admin: {response.text}"
            )

        return response.json()["access_token"]

    # =========================================================
    # VALIDAR JWT
    # =========================================================

    def validate_token(self, credentials: HTTPAuthorizationCredentials):
        try:
            token = credentials.credentials
            payload = jwt.get_unverified_claims(token)
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido")

    # =========================================================
    # EXTRAIR ROLES
    # =========================================================

    def extract_roles(self, payload: dict):
        # Tenta claim "roles" direto (configurado pelo domain-roles scope do Keycloak)
        roles = payload.get("roles", [])
        if roles:
            return roles
        # Fallback para realm_access.roles
        return payload.get("realm_access", {}).get("roles", [])

    # =========================================================
    # CRIAR USUÁRIO
    # =========================================================

    def create_user(self, user_data: dict):
        admin_token = self.get_admin_token()

        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "username": user_data["email"],
            "email": user_data["email"],
            "enabled": True,
            "firstName": user_data["name"]
        }

        response = requests.post(self.users_url, json=payload, headers=headers)

        if response.status_code not in [201, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao criar usuário no Keycloak: {response.text}"
            )

    # =========================================================
    # ATUALIZAR ROLES
    # =========================================================

    def update_roles(self, user_id, roles):
        # TODO: implementar
        pass

    # =========================================================
    # DELETAR USUÁRIO
    # =========================================================

    def delete_user(self, keycloak_user_id):
        admin_token = self.get_admin_token()

        headers = {"Authorization": f"Bearer {admin_token}"}

        response = requests.delete(
            f"{self.users_url}/{keycloak_user_id}",
            headers=headers
        )

        if response.status_code != 204:
            raise HTTPException(
                status_code=500,
                detail="Falha ao deletar usuário no Keycloak"
            )