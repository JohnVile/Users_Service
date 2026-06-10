from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.integrations.keycloak_client import KeycloakClient
from app.integrations.rabbitmq_client import RabbitMQClient
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import PageMetadata, UserPage, UserResponse, UserUpdate

import logging
logger = logging.getLogger(__name__)

class UserService:

    def __init__(self):
        self.repository = UserRepository()
        self.keycloak = KeycloakClient()
        self.publisher = RabbitMQClient()

    # =========================================================
    # HELPERS INTERNOS
    # =========================================================

    def _verificar_acesso_self_ou_manager(self, usuario, current_user: dict) -> None:
        """
        Lança 403 se o usuário atual não é MANAGER e não é o dono do recurso.
        A comparação de 'self' usa e-mail, pois o 'sub' do JWT (UUID Keycloak)
        difere do ID de domínio (usr_xxx).
        """
        if "MANAGER" in current_user.get("roles", []):
            return
        if current_user.get("email") != usuario.email:
            raise HTTPException(status_code=403, detail="Acesso negado")

    # =========================================================
    # CRIAR USUÁRIO — POST /users
    # =========================================================

    def criacao_de_usuario(self, db: Session, user_data):
        if self.repository.busca_usuario_por_email(db, user_data.email):
            raise HTTPException(status_code=409, detail="Esse email já está em uso")

        data = user_data.model_dump()
        data["roles"] = ",".join(data["roles"])

        usuario_criado = self.repository.cria_usuario(db, data)

        # Registra no Keycloak com as roles iniciais
        # Se falhar, o cadastro local é mantido; o admin pode recriar manualmente.
        try:
            self.keycloak.create_user(user_data.model_dump())
        except Exception as e:
            logger.warning(f"[Keycloak] Falha ao criar usuário: {e}")

        return usuario_criado

    # =========================================================
    # LISTAR USUÁRIOS — GET /users
    # =========================================================

    def lista_de_usuarios(
        self,
        db: Session,
        status: str | None = None,
        role: str | None = None,
        page: int = 0,
        size: int = 20,
    ) -> UserPage:
        items, total = self.repository.lista_usuarios(
            db, status=status, role=role, page=page, size=size
        )
        total_pages = ceil(total / size) if size > 0 else 0
        return UserPage(
            items=[UserResponse.model_validate(u) for u in items],
            page=PageMetadata(
                page=page,
                size=size,
                totalElements=total,
                totalPages=total_pages,
            ),
        )

    # =========================================================
    # BUSCAR POR ID — GET /users/{userId}
    # =========================================================

    def obter_usuario(self, db: Session, user_id: str, current_user: dict = None):
        usuario = self.repository.busca_usuario_por_id(db, user_id)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        if current_user is not None:
            self._verificar_acesso_self_ou_manager(usuario, current_user)

        return usuario

    # =========================================================
    # ATUALIZAR DADOS — PATCH /users/{userId}
    # =========================================================
    def atualizar_dados_usuario(
            self, db: Session, user_id: str, user_data: UserUpdate, current_user: dict
    ):
        usuario = self.obter_usuario(db, user_id, current_user)

        data = {k: v for k, v in user_data.model_dump().items() if v is not None}
        if not data:
            return usuario  # Sem alterações
        return self.repository.atualiza_dados_do_usuario(db, usuario, data)

    # =========================================================
    # DESATIVAR USUÁRIO — DELETE /users/{userId}
    # =========================================================

    def desativar_usuario(
        self, db: Session, user_id: str, reason: str, current_user: dict
    ):
        usuario = self.obter_usuario(db, user_id, current_user)

        if usuario.status == "INACTIVE":
            raise HTTPException(status_code=409, detail="Usuário já está inativo")

        data = {
            "status": "INACTIVE",
            "deactivated_at": datetime.now(timezone.utc),
        }
        usuario_atualizado = self.repository.atualiza_dados_do_usuario(
            db, usuario, data
        )

        # Desabilita conta no Keycloak
        try:
            self.keycloak.disable_user(usuario.email)
        except Exception as e:
            logger.warning(f"[Keycloak] Falha ao desabilitar usuário: {e}")

        # Publica evento com envelope completo (async-docs.yaml)
        self.publisher.publish_user_deactivated(user_id, reason)

        return usuario_atualizado

    # =========================================================
    # ATUALIZAR PAPÉIS — PUT /users/{userId}/roles
    # =========================================================

    def atualiza_papeis_usuario(
        self,
        db: Session,
        user_id: str,
        roles: list[str],
        current_user: dict,
    ):
        # Proteção: MANAGER não pode remover o próprio papel de MANAGER.
        # Usa e-mail para correlacionar JWT com registro de domínio.
        current_domain_user = self.repository.busca_usuario_por_email(
            db, current_user.get("email", "")
        )
        if (
            current_domain_user
            and current_domain_user.id == user_id
            and "MANAGER" not in roles
        ):
            raise HTTPException(
                status_code=403,
                detail="Gerentes não podem remover seu próprio papel de MANAGER",
            )

        usuario = self.obter_usuario(db, user_id)
        usuario_atualizado = self.repository.atualiza_papeis_usuario(
            db, usuario, roles
        )

        # Reflete as novas roles no Keycloak
        try:
            self.keycloak.update_roles(usuario.email, roles)
        except Exception as e:
            logger.warning(f"[Keycloak] Falha ao atualizar papéis: {e}")

        return usuario_atualizado
