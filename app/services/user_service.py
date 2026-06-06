from math import ceil

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import PageMetadata, UserPage, UserResponse
from app.integrations.keycloack_client import KeycloakClient
from app.integrations.rabbitmq_client import RabbitMQClient

'''
Escopo funcional: 

- Criar usuário no domínio e no Keycloak.   - ✅FEITO
- Listar usuários com filtros e paginação.  - ✅FEITO
- Buscar usuário por identificador.         - ✅FEITO
- Atualizar dados básicos do usuário.       - ❌FALTA AJUSTAR
- Desativar usuário logicamente.            - ✅FEITO
- Substituir papéis (`roles`) do usuário.   - ❌FALTA AJUSTAR
'''

class UserService:

    def __init__(self):
        self.repository = UserRepository()
        self.keycloak = KeycloakClient()
        self.publisher = RabbitMQClient()

    # =========================================================
    # CRIAR USUÁRIO
    # =========================================================
    def criacao_de_usuario(self, db: Session, user_data):
        usuario_existente = self.repository.busca_usuario_por_email(db, user_data.email)

        if usuario_existente:
            raise HTTPException(
                status_code=409,
                detail="Esse email já está em uso"
            )

        # Converte roles de list para string para salvar no banco
        data = user_data.model_dump()
        data["roles"] = ",".join(data["roles"])

        # Salva no banco local
        usuario_criado = self.repository.cria_usuario(db, data)

        # Cria no Keycloak (se falhar, loga mas não desfaz o cadastro local por ora)
        try:
            self.keycloak.create_user(user_data.model_dump())
        except Exception as e:
            print(f"[Keycloak] Falha ao criar usuário: {e}")

        return usuario_criado

    # =========================================================
    # LISTAR USUÁRIOS
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
            items=[UserResponse.model_validate(user) for user in items],
            page=PageMetadata(
                page=page,
                size=size,
                totalElements=total,
                totalPages=total_pages,
            ),
        )

    # =========================================================
    # BUSCAR POR ID
    # =========================================================
    def obter_usuario(self, db: Session, user_id: str):
        usuario_existente = self.repository.busca_usuario_por_id(db, user_id)
        if not usuario_existente:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )
        return usuario_existente

    # =========================================================
    # DESATIVAR USUÁRIO
    # =========================================================
    def desativar_usuario(self, db: Session, user_id: str):
        usuario_existente = self.obter_usuario(db, user_id)
        if not usuario_existente:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )
        if usuario_existente.status == "INACTIVE":
            raise HTTPException(
                status_code=400,
                detail="Usuário já está inativo"
            )
        usuario_existente.status = "INACTIVE"
        db.commit()
        self.publisher.publish_user_deactivated(user_id)
        return usuario_existente
    
    # =========================================================
    # ATUALIZAR PAPÉIS DO USUÁRIO
    # =========================================================
    def atualiza_papeis_usuario(
            self, 
            db: Session, 
            user_id: str, 
            roles: list[str], 
            current_user_id: str
        ):

        # gerentes não podem remover seu próprio papel de MANAGER
        if user_id == current_user_id and "MANAGER" not in roles:
            raise HTTPException(
                status_code=403,
                detail="Gerentes não podem remover seu próprio papel de MANAGER"
            )
        
        usuario_existente = self.obter_usuario(db, user_id)
        
        usuario_atualizado = self.repository.atualiza_papeis_usuario(db, usuario_existente, roles)

        try:
            self.keycloak.update_roles(usuario_existente.email, roles)
        except Exception as e:
            print(f"[Keycloak] Falha ao atualizar papéis do usuário: {e}")
            
        return usuario_atualizado