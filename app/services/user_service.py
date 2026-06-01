from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.integrations.keycloack_client import KeycloakClient
from app.integrations.rabbitmq_client import RabbitMQClient

'''
Escopo funcional: 

- Criar usuário no domínio e no Keycloak.   - ✅FEITO
- Listar usuários com filtros e paginação.  - ❌FALTA AJUSTAR
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
    def lista_de_usuarios(self, db: Session):
        return self.repository.lista_todos_os_usuarios(db)

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