import requests

from jose import JWTError, jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings

_HTTP_TIMEOUT = 5  # segundos


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
    def admin_token_url(self) -> str:
        return f"{self.server_url}/realms/master/protocol/openid-connect/token"

    @property
    def users_url(self) -> str:
        return f"{self.server_url}/admin/realms/{self.realm}/users"

    def _realm_roles_url(self, role_name: str) -> str:
        return f"{self.server_url}/admin/realms/{self.realm}/roles/{role_name}"

    def _user_roles_url(self, keycloak_user_id: str) -> str:
        return f"{self.users_url}/{keycloak_user_id}/role-mappings/realm"

    def get_oidc_config(self) -> dict:
        if self._oidc_config is None:
            url = f"{self.server_url}/realms/{self.realm}/.well-known/openid-configuration"
            response = requests.get(url, timeout=_HTTP_TIMEOUT)
            response.raise_for_status()
            self._oidc_config = response.json()
        return self._oidc_config

    @property
    def issuer(self) -> str:
        config = self.get_oidc_config()
        issuer = config["issuer"]
        # Tokens obtidos via localhost:8080 trazem iss com localhost, mesmo quando o
        # serviço acessa o Keycloak via host.docker.internal dentro do container.
        if "host.docker.internal" in issuer:
            return issuer.replace("host.docker.internal", "localhost")
        return issuer

    @property
    def certs_url(self) -> str:
        return self.get_oidc_config()["jwks_uri"]

    # =========================================================
    # ADMIN TOKEN
    # =========================================================

    def get_admin_token(self) -> str:
        """Obtém token de administrador via realm master / admin-cli."""
        data = {
            "client_id": "admin-cli",
            "username": settings.KEYCLOAK_ADMIN_USER,
            "password": settings.KEYCLOAK_ADMIN_PASSWORD,
            "grant_type": "password",
        }
        response = requests.post(
            self.admin_token_url, data=data, timeout=_HTTP_TIMEOUT
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao autenticar no Keycloak admin: {response.text}",
            )
        return response.json()["access_token"]

    def _admin_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.get_admin_token()}",
            "Content-Type": "application/json",
        }

    # =========================================================
    # VALIDAR JWT
    # =========================================================

    def validate_token(self, credentials: HTTPAuthorizationCredentials) -> dict:
        token = credentials.credentials
        try:
            jwks_response = requests.get(self.certs_url, timeout=_HTTP_TIMEOUT)
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

    def extract_roles(self, payload: dict) -> list[str]:
        # Claim "roles" configurada pelo client scope "domain-roles" do Keycloak
        roles = payload.get("roles", [])
        if roles:
            return roles
        # Fallback para realm_access.roles
        return payload.get("realm_access", {}).get("roles", [])

    # =========================================================
    # HELPERS INTERNOS DE ROLES
    # =========================================================

    def _fetch_role_objects(self, role_names: list[str], headers: dict) -> list[dict]:
        """
        Busca os objetos de role pelo nome no Keycloak.
        Ignora silenciosamente roles que não existem no realm.
        """
        role_objects = []
        for role in role_names:
            resp = requests.get(
                self._realm_roles_url(role),
                headers=headers,
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code == 200:
                role_objects.append(resp.json())
            else:
                print(f"[Keycloak] Role '{role}' não encontrada no realm ({resp.status_code})")
        return role_objects

    def _assign_roles_to_user(
        self, keycloak_user_id: str, roles: list[str], headers: dict
    ) -> None:
        """Atribui roles de realm a um usuário do Keycloak."""
        role_objects = self._fetch_role_objects(roles, headers)
        if not role_objects:
            return

        resp = requests.post(
            self._user_roles_url(keycloak_user_id),
            headers=headers,
            json=role_objects,
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao atribuir roles no Keycloak: {resp.text}",
            )

    def _remove_all_realm_roles(
        self, keycloak_user_id: str, headers: dict
    ) -> None:
        """Remove todas as roles de realm do usuário."""
        resp = requests.get(
            self._user_roles_url(keycloak_user_id),
            headers=headers,
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return

        current_roles = resp.json()
        if not current_roles:
            return

        del_resp = requests.delete(
            self._user_roles_url(keycloak_user_id),
            headers=headers,
            json=current_roles,
            timeout=_HTTP_TIMEOUT,
        )
        if del_resp.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao remover roles no Keycloak: {del_resp.text}",
            )

    # =========================================================
    # CRIAR USUÁRIO
    # =========================================================

    def create_user(self, user_data: dict) -> None:
        """
        Cria usuário no Keycloak e atribui as roles informadas.
        Em caso de conflito (409), ignora silenciosamente.
        """
        headers = self._admin_headers()
        payload = {
            "username": user_data["email"],
            "email": user_data["email"],
            "enabled": True,
            "firstName": user_data["name"],
        }

        resp = requests.post(
            self.users_url, json=payload, headers=headers, timeout=_HTTP_TIMEOUT
        )

        if resp.status_code == 409:
            # Usuário já existe no Keycloak — sem problema
            print(f"[Keycloak] Usuário {user_data['email']} já existe no realm.")
            return

        if resp.status_code not in [201, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao criar usuário no Keycloak: {resp.text}",
            )

        # Extrai o ID do Keycloak a partir do header Location
        # Exemplo: .../admin/realms/facoffee/users/<uuid>
        location = resp.headers.get("Location", "")
        keycloak_user_id = location.rstrip("/").split("/")[-1] if location else None

        if not keycloak_user_id:
            print("[Keycloak] Não foi possível extrair o ID do usuário criado.")
            return

        # Atribui as roles iniciais
        roles = user_data.get("roles") or ["PARTICIPANT"]
        self._assign_roles_to_user(keycloak_user_id, roles, headers)

    # =========================================================
    # ATUALIZAR ROLES
    # =========================================================

    def update_roles(self, email: str, roles: list[str]) -> None:
        """
        Substitui integralmente as roles de realm do usuário no Keycloak.
        1. Localiza o usuário pelo e-mail.
        2. Remove todas as roles atuais.
        3. Atribui as novas roles.
        """
        headers = self._admin_headers()

        # 1. Localizar usuário pelo e-mail
        resp = requests.get(
            self.users_url,
            headers=headers,
            params={"email": email, "exact": True},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()

        users = resp.json()
        if not users:
            raise HTTPException(
                status_code=404,
                detail=f"Usuário '{email}' não encontrado no Keycloak",
            )

        keycloak_user_id = users[0]["id"]

        # 2. Remover roles atuais
        self._remove_all_realm_roles(keycloak_user_id, headers)

        # 3. Atribuir novas roles
        self._assign_roles_to_user(keycloak_user_id, roles, headers)

    # =========================================================
    # DESATIVAR USUÁRIO NO KEYCLOAK (desabilita a conta)
    # =========================================================

    def disable_user(self, email: str) -> None:
        """Desabilita a conta do usuário no Keycloak (enabled: false)."""
        headers = self._admin_headers()

        resp = requests.get(
            self.users_url,
            headers=headers,
            params={"email": email, "exact": True},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()

        users = resp.json()
        if not users:
            print(f"[Keycloak] Usuário '{email}' não encontrado para desabilitar.")
            return

        keycloak_user_id = users[0]["id"]

        update_resp = requests.put(
            f"{self.users_url}/{keycloak_user_id}",
            headers=headers,
            json={"enabled": False},
            timeout=_HTTP_TIMEOUT,
        )
        if update_resp.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao desabilitar usuário no Keycloak: {update_resp.text}",
            )
