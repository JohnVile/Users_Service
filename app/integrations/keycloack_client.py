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
        self._oidc_config = None

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

    def get_oidc_config(self):
        if self._oidc_config is None:
            discovery_url = (
                f"{self.server_url}/realms/{self.realm}"
                "/.well-known/openid-configuration"
            )
            response = requests.get(discovery_url, timeout=5)
            response.raise_for_status()
            self._oidc_config = response.json()
        return self._oidc_config

    @property
    def issuer(self):
        config = self.get_oidc_config()
        issuer = config["issuer"]

        # Tokens obtidos em localhost:8080 trazem iss com localhost, mesmo
        # quando o serviço acessa o Keycloak via host.docker.internal.
        if "host.docker.internal" in issuer:
            return issuer.replace("host.docker.internal", "localhost")

        return issuer

    @property
    def certs_url(self):
        return self.get_oidc_config()["jwks_uri"]

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
        token = credentials.credentials

        try:
            jwks_response = requests.get(self.certs_url, timeout=5)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}

            for key in jwks.get("keys", []):
                if key.get("kid") == unverified_header.get("kid"):
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"],
                    }
                    break

            if not rsa_key:
                raise HTTPException(status_code=401, detail="Token inválido")

            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                issuer=self.issuer,
                options={"verify_aud": False},
            )
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido")
        except requests.RequestException:
            raise HTTPException(
                status_code=503,
                detail="Serviço de autenticação indisponível",
            )

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
    def update_roles(self, email: str, roles: list[str]):

        admin_token = self.get_admin_token()
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            self.users_url,
            headers=headers,
            params={"email": email, "exact": True}
        )

        users = response.json()
        if not users:
            raise HTTPException(
                status_code=404, 
                detail="Usuário não encontrado no Keycloak"
            )
        keycloak_user_id = users[0]["id"]


        # 2 - busca os objetos de role no Keycloak para enviar na atribuição
        role_objects = []
        for role in roles:
            role_response = requests.get(
                f"{self.server_url}/admin/realms/{self.realm}/roles/{role}",
                headers=headers
            )
            role_objects.append(role_response.json())
        
        # 3 - remove role atual
        current_roles_response = requests.get(
            f"{self.users_url}/{keycloak_user_id}/role-mappings/realm",
            headers=headers
        )

        if current_roles_response.status_code == 200:
            current_roles = current_roles_response.json()
            if current_roles:
                delete_response = requests.delete(
                    f"{self.users_url}/{keycloak_user_id}/role-mappings/realm",
                    headers=headers,
                    json=current_roles
                )
                if delete_response.status_code not in [200, 204]:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Falha ao remover roles atuais no Keycloak: {delete_response.status_code}"
                    )
                print(f"[Keycloak] Roles atuais removidas do usuário {email}")

        # 4 - atribui novas roles
        assign_response = requests.post(
            f"{self.users_url}/{keycloak_user_id}/role-mappings/realm",
            headers=headers,
            json=role_objects
        )

        if assign_response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao atualizar roles no Keycloak:{assign_response.text}"
            )
        

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