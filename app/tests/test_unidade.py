"""
TESTES UNITÁRIOS

Finalidade:
Testar regras de negócio isoladamente, sem chamadas HTTP,
sem banco de dados real e sem integrações externas.

Exemplos de responsabilidades:
- Validações de entrada
- Regras de negócio
- Regras de status
- Regras de papéis (roles)
- Regras de e-mail único
- Regras de atualização
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate
from app.schemas.user_schema import UserUpdate

# ─── Helpers internos ─────────────────────────────────────────────────────────
def _servico():
    """Cria UserService com todas as dependências externas mockadas."""
    s = UserService()
    s.repository = MagicMock()
    s.keycloak = MagicMock()
    s.publisher = MagicMock()
    return s


def _usuario_mock(
    user_id="usr_abc123",
    name="Test User",
    email="test@test.com",
    status="ACTIVE",
    roles="PARTICIPANT",
):
    """Cria um objeto mock que simula um registro User do banco."""
    u = MagicMock()
    u.id = user_id
    u.name = name
    u.email = email
    u.status = status
    u.roles = roles
    return u

# ─── POST /users ─────────────────────────────────────────────────────────────
class TestCriacaoDeUsuario:

    def test_criacao_bem_sucedida_retorna_usuario(self):
        """Quando email não existe, o usuário é criado e retornado."""
        s = _servico()
        mock_user = _usuario_mock()
        s.repository.busca_usuario_por_email.return_value = None
        s.repository.cria_usuario.return_value = mock_user

        resultado = s.criacao_de_usuario(
            MagicMock(), UserCreate(name="Test User", email="test@test.com")
        )

        assert resultado == mock_user
        s.repository.cria_usuario.assert_called_once()

    def test_sem_roles_usa_participant_como_padrao(self):
        """Quando roles não é informado, o padrão PARTICIPANT é aplicado."""
        s = _servico()
        s.repository.busca_usuario_por_email.return_value = None
        s.repository.cria_usuario.return_value = _usuario_mock()

        data = UserCreate(name="Test User", email="test@test.com")
        assert data.roles == ["PARTICIPANT"]  # validação do schema

        s.criacao_de_usuario(MagicMock(), data)

        args_enviados = s.repository.cria_usuario.call_args[0][1]
        assert args_enviados["roles"] == "PARTICIPANT"

    def test_email_duplicado_lanca_409(self):
        """Quando email já existe no domínio, lança HTTPException 409."""
        s = _servico()
        s.repository.busca_usuario_por_email.return_value = _usuario_mock()

        with pytest.raises(HTTPException) as exc:
            s.criacao_de_usuario(
                MagicMock(), UserCreate(name="Outro User", email="dup@test.com")
            )

        assert exc.value.status_code == 409

    def test_roles_sao_salvas_como_string_separada_por_virgula(self):
        """Roles são convertidas de lista para string antes de salvar no banco."""
        s = _servico()
        s.repository.busca_usuario_por_email.return_value = None
        s.repository.cria_usuario.return_value = _usuario_mock(roles="MANAGER,PARTICIPANT")

        s.criacao_de_usuario(
            MagicMock(),
            UserCreate(name="Test", email="test@test.com", roles=["MANAGER", "PARTICIPANT"]),
        )

        args = s.repository.cria_usuario.call_args[0][1]
        assert args["roles"] == "MANAGER,PARTICIPANT"

    def test_falha_no_keycloak_nao_impede_criacao_no_dominio(self):
        """
        Keycloak offline não deve bloquear o cadastro local.
        O usuário é salvo no banco mesmo que a integração falhe.
        """
        s = _servico()
        mock_user = _usuario_mock()
        s.repository.busca_usuario_por_email.return_value = None
        s.repository.cria_usuario.return_value = mock_user
        s.keycloak.create_user.side_effect = Exception("Keycloak indisponível")

        resultado = s.criacao_de_usuario(
            MagicMock(), UserCreate(name="Test User", email="test@test.com")
        )

        assert resultado == mock_user
        s.repository.cria_usuario.assert_called_once()

# ─── GET /users ──────────────────────────────────────────────────────────────
# Testes unitários relacionados a filtros, paginação e permissões.


# ─── GET /users/{userId} ───────────────────────────────────────────────────
# Testes unitários relacionados à busca de usuário.


# ─── PATCH /users/{userId} ───────────────────────────────────────────────────
class TestAtualizarDadosUsuarioUnitario:
 
    # ── Caminho feliz ──────────────────────────────────────────────────────
 
    def test_atualiza_nome_com_sucesso(self):
        """Atualizar name com dado válido deve chamar o repositório e retornar o usuário."""
        s = _servico()
        current_user = {"email": "test@test.com", "roles": ["PARTICIPANT"]}
        mock_user = _usuario_mock()
        mock_atualizado = _usuario_mock(name="Novo Nome")
 
        s.repository.busca_usuario_por_id.return_value = mock_user
        s.repository.atualiza_dados_do_usuario.return_value = mock_atualizado
 
        resultado = s.atualizar_dados_usuario(
            MagicMock(), "usr_abc123", UserUpdate(name="Novo Nome"), current_user
        )
 
        assert resultado.name == "Novo Nome"
        s.repository.atualiza_dados_do_usuario.assert_called_once()
 
    def test_payload_vazio_retorna_usuario_sem_alteracoes(self):
        """
        Se UserUpdate não tiver nenhum campo preenchido (todos None),
        o repositório NÃO deve ser chamado e o usuário original é retornado.
        """
        s = _servico()
        current_user = {"email": "test@test.com", "roles": ["PARTICIPANT"]}
        mock_user = _usuario_mock()
 
        s.repository.busca_usuario_por_id.return_value = mock_user
 
        resultado = s.atualizar_dados_usuario(
            MagicMock(), "usr_abc123", UserUpdate(), current_user
        )
 
        assert resultado == mock_user
        s.repository.atualiza_dados_do_usuario.assert_not_called()
 
    # ── 404 ────────────────────────────────────────────────────────────────
 
    def test_usuario_inexistente_lanca_404(self):
        """Tentar atualizar ID que não existe deve lançar HTTPException 404."""
        s = _servico()
        current_user = {"email": "manager@test.com", "roles": ["MANAGER"]}
        s.repository.busca_usuario_por_id.return_value = None
 
        with pytest.raises(HTTPException) as exc:
            s.atualizar_dados_usuario(
                MagicMock(), "usr_naoexiste", UserUpdate(name="Qualquer"), current_user
            )
 
        assert exc.value.status_code == 404
 
    # ── Validação de schema ────────────────────────────────────────────────
 
    def test_name_com_menos_de_3_chars_invalido_no_schema(self):
        """UserUpdate com name menor que 3 caracteres deve levantar ValidationError."""
        from pydantic import ValidationError
 
        with pytest.raises(ValidationError):
            UserUpdate(name="AB")
 
    def test_apenas_campos_preenchidos_sao_enviados_ao_repositorio(self):
        """
        O dict enviado ao repositório deve conter apenas os campos
        não-nulos de UserUpdate — atualmente somente 'name'.
        """
        s = _servico()
        current_user = {"email": "test@test.com", "roles": ["PARTICIPANT"]}
        mock_user = _usuario_mock()
 
        s.repository.busca_usuario_por_id.return_value = mock_user
        s.repository.atualiza_dados_do_usuario.return_value = mock_user
 
        s.atualizar_dados_usuario(
            MagicMock(), "usr_abc123", UserUpdate(name="Bom Nome"), current_user
        )
 
        _, _, kwargs_data = s.repository.atualiza_dados_do_usuario.call_args[0]
        assert "name" in kwargs_data
        # Garantir que nenhum campo None vazou
        assert all(v is not None for v in kwargs_data.values())


# ─── DELETE /users/{userId} ───────────────────────────────────────────────────
class TestDesativarUsuario:

    def test_desativar_usuario_ativo_muda_status_para_inactive(self):
        """Desativar usuário ACTIVE deve atualizar o status para INACTIVE."""
        s = _servico()
        current_user = {"email": "manager@test.com", "roles": ["MANAGER"]}
        mock_user = _usuario_mock(status="ACTIVE")
        mock_atualizado = _usuario_mock(status="INACTIVE")

        s.repository.busca_usuario_por_id.return_value = mock_user
        s.repository.atualiza_dados_do_usuario.return_value = mock_atualizado

        resultado = s.desativar_usuario(MagicMock(), "usr_abc123", "Motivo", current_user)

        assert resultado.status == "INACTIVE"
        s.repository.atualiza_dados_do_usuario.assert_called_once()

    def test_desativar_usuario_ja_inativo_lanca_409(self):
        """Tentar desativar usuário que já é INACTIVE deve lançar HTTPException 409."""
        s = _servico()
        current_user = {"email": "manager@test.com", "roles": ["MANAGER"]}
        s.repository.busca_usuario_por_id.return_value = _usuario_mock(status="INACTIVE")

        with pytest.raises(HTTPException) as exc:
            s.desativar_usuario(MagicMock(), "usr_abc123", "Motivo", current_user)

        assert exc.value.status_code == 409

    def test_desativar_usuario_inexistente_lanca_404(self):
        """Tentar desativar ID que não existe deve lançar HTTPException 404."""
        s = _servico()
        current_user = {"email": "manager@test.com", "roles": ["MANAGER"]}
        s.repository.busca_usuario_por_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            s.desativar_usuario(MagicMock(), "usr_inexistente", "Motivo", current_user)

        assert exc.value.status_code == 404

    def test_manager_pode_desativar_qualquer_usuario(self):
        """MANAGER pode desativar usuários com e-mail diferente do seu."""
        s = _servico()
        current_user = {"email": "manager@test.com", "roles": ["MANAGER"]}
        mock_user = _usuario_mock(email="outro@test.com", status="ACTIVE")

        s.repository.busca_usuario_por_id.return_value = mock_user
        s.repository.atualiza_dados_do_usuario.return_value = mock_user

        # Não deve lançar exceção
        s.desativar_usuario(MagicMock(), "usr_outro", "Motivo", current_user)

    def test_participant_pode_desativar_a_propria_conta(self):
        """PARTICIPANT pode desativar quando o e-mail do token bate com o do usuário alvo."""
        s = _servico()
        current_user = {"email": "participant@test.com", "roles": ["PARTICIPANT"]}
        mock_user = _usuario_mock(email="participant@test.com", status="ACTIVE")

        s.repository.busca_usuario_por_id.return_value = mock_user
        s.repository.atualiza_dados_do_usuario.return_value = mock_user

        # Não deve lançar exceção
        s.desativar_usuario(MagicMock(), "usr_part", "Saindo", current_user)

    def test_participant_nao_pode_desativar_conta_de_outro_lanca_403(self):
        """PARTICIPANT tentando desativar outro usuário deve receber HTTPException 403."""
        s = _servico()
        current_user = {"email": "participant@test.com", "roles": ["PARTICIPANT"]}
        mock_user = _usuario_mock(email="outro@test.com", status="ACTIVE")

        s.repository.busca_usuario_por_id.return_value = mock_user

        with pytest.raises(HTTPException) as exc:
            s.desativar_usuario(MagicMock(), "usr_outro", "Tentativa", current_user)

        assert exc.value.status_code == 403

    def test_evento_user_deactivated_e_publicado_no_rabbitmq(self):
        """O evento UserDeactivated deve ser publicado com userId e reason corretos."""
        s = _servico()
        current_user = {"email": "manager@test.com", "roles": ["MANAGER"]}
        mock_user = _usuario_mock(user_id="usr_abc123", status="ACTIVE")

        s.repository.busca_usuario_por_id.return_value = mock_user
        s.repository.atualiza_dados_do_usuario.return_value = mock_user

        s.desativar_usuario(MagicMock(), "usr_abc123", "Motivo do evento", current_user)

        s.publisher.publish_user_deactivated.assert_called_once_with(
            "usr_abc123", "Motivo do evento"
        )

# ─── PUT /users/{userId}/roles ───────────────────────────────────────────────────
# Testes unitários relacionados à substituição de papéis.
