"""
conftest.py — Configurações compartilhadas dos testes.

Responsabilidades deste arquivo:
1. Definir variáveis de ambiente necessárias para a aplicação iniciar.
2. Criar um banco SQLite em memória para os testes.
3. Sobrescrever dependências do FastAPI (banco e autenticação).
4. Mockar integrações externas (Keycloak e RabbitMQ).
5. Disponibilizar fixtures reutilizáveis para todos os testes.

OBS:
As variáveis de ambiente devem ser definidas antes dos imports da aplicação,
pois o pydantic-settings carrega as configurações durante a importação.
"""
import os

# ---------------------------------------------------------------------------
# Variáveis de ambiente utilizadas exclusivamente durante os testes.
# Evitam dependências de serviços reais e permitem que a aplicação inicialize
# corretamente sem necessidade de infraestrutura externa.
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("KEYCLOAK_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "facoffee")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "test-client")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "test-secret")
os.environ.setdefault("KEYCLOAK_ADMIN_USER", "admin")
os.environ.setdefault("KEYCLOAK_ADMIN_PASSWORD", "admin")
os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("RABBITMQ_PORT", "5672")
os.environ.setdefault("RABBITMQ_USER", "test")
os.environ.setdefault("RABBITMQ_PASSWORD", "test")

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user_model import User, gerar_id

# ---------------------------------------------------------------------------
# Banco de dados de testes.
#
# Utiliza SQLite em memória para garantir execução rápida e isolamento.
# O StaticPool mantém uma única conexão compartilhada durante o teste,
# evitando que o banco seja recriado a cada nova sessão.
# ---------------------------------------------------------------------------
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=TEST_ENGINE
)

# ---------------------------------------------------------------------------
# Métodos externos que não devem ser executados durante os testes.
#
# Todos serão substituídos por mocks através do unittest.mock.patch,
# evitando chamadas reais para Keycloak e RabbitMQ.
# ---------------------------------------------------------------------------
_PATCHES = [
    "app.integrations.keycloak_client.KeycloakClient.create_user",
    "app.integrations.keycloak_client.KeycloakClient.disable_user",
    "app.integrations.keycloak_client.KeycloakClient.update_roles",
    "app.integrations.rabbitmq_client.RabbitMQClient.publish_user_deactivated",
]

# ---------------------------------------------------------------------------
# Payloads simulados de autenticação.
#
# Representam o retorno da função get_current_user após a validação
# de um JWT. Permitem testar autorização sem gerar tokens reais.
# ---------------------------------------------------------------------------
MANAGER_PAYLOAD = {
    "sub": "mgr-sub",
    "email": "manager@test.com",
    "roles": ["MANAGER"]
}

PARTICIPANT_PAYLOAD = {
    "sub": "part-sub",
    "email": "participant@test.com",
    "roles": ["PARTICIPANT"]
}

# ===========================================================================
# FIXTURES DE BANCO DE DADOS
# ===========================================================================

@pytest.fixture(scope="function")
def db():
    """
    Cria todas as tabelas antes de cada teste e remove tudo ao final.

    Benefícios:
    - Isolamento entre testes.
    - Nenhum dado vaza de um teste para outro.
    - Estado previsível para cada execução.
    """
    Base.metadata.create_all(bind=TEST_ENGINE)

    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=TEST_ENGINE)


def _override_db(session):
    """
    Substitui a dependência get_db da aplicação.

    Faz com que os endpoints utilizem a sessão SQLite criada
    especificamente para o teste atual.
    """
    def inner():
        yield session
    return inner


# ===========================================================================
# FIXTURES DE CLIENTE HTTP
# ===========================================================================

@pytest.fixture
def client(db):
    """
    Cliente HTTP sem autenticação.

    Utilizado para testar endpoints públicos ou cenários onde
    autenticação não é necessária.
    """
    app.dependency_overrides[get_db] = _override_db(db)

    with patch(_PATCHES[0]), patch(_PATCHES[1]), patch(_PATCHES[2]), patch(_PATCHES[3]):
        yield TestClient(app, raise_server_exceptions=True)

    app.dependency_overrides.clear()


@pytest.fixture
def client_manager(db):
    """
    Cliente autenticado como MANAGER.

    Sobrescreve a dependência get_current_user para simular um
    usuário com privilégios administrativos.
    """
    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: {**MANAGER_PAYLOAD}

    with patch(_PATCHES[0]), patch(_PATCHES[1]), patch(_PATCHES[2]), patch(_PATCHES[3]):
        yield TestClient(app, raise_server_exceptions=True)

    app.dependency_overrides.clear()


@pytest.fixture
def client_participant(db):
    """
    Cliente autenticado como PARTICIPANT.

    Utilizado para validar regras de autorização e verificar
    comportamentos permitidos ou negados para usuários comuns.
    """
    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: {**PARTICIPANT_PAYLOAD}

    with patch(_PATCHES[0]), patch(_PATCHES[1]), patch(_PATCHES[2]), patch(_PATCHES[3]):
        yield TestClient(app, raise_server_exceptions=True)

    app.dependency_overrides.clear()


# ===========================================================================
# FIXTURE FÁBRICA DE USUÁRIOS
# ===========================================================================

@pytest.fixture
def criar_usuario(db):
    """
    Factory fixture para criação de usuários diretamente no banco.

    Objetivo:
    Evitar repetição de código em múltiplos testes.

    Exemplo:
        usuario = criar_usuario(
            email="teste@email.com",
            status="ACTIVE"
        )
    """
    def _criar(
        name: str = "Usuário Teste",
        email: str = "usuario@test.com",
        status: str = "ACTIVE",
        roles: str = "PARTICIPANT",
    ):
        user = User(
            id=gerar_id(),
            name=name,
            email=email,
            status=status,
            roles=roles,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    return _criar