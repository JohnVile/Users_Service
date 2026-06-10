"""
TESTES DE AUTORIZAÇÃO

Finalidade:
Validar regras de acesso baseadas em JWT e Roles.

Os testes devem verificar:
- Acesso permitido para MANAGER
- Acesso negado quando necessário
- Restrições para PARTICIPANT
- Acesso ao próprio recurso
- Acesso a recursos de terceiros
"""
import pytest

# ─── POST /users ─────────────────────────────────────────────────────────────
class TestAutorizacaoPostUsers:

    def test_endpoint_publico_sem_token_e_aceito(self, client):
        """
        POST /users é público (security: [] no api-docs).
        Requisição sem Authorization header deve funcionar normalmente.
        """
        payload = {"name": "Sem Token", "email": "semtoken@test.com"}

        resp = client.post("/api/users", json=payload)

        assert resp.status_code == 201

    def test_com_token_de_manager_tambem_funciona(self, client_manager):
        """POST /users deve aceitar requisições com token de qualquer role."""
        payload = {"name": "Com Token", "email": "comtoken@test.com"}

        resp = client_manager.post("/api/users", json=payload)

        assert resp.status_code == 201

    def test_com_token_de_participant_tambem_funciona(self, client_participant):
        """POST /users deve aceitar requisições com token de PARTICIPANT."""
        payload = {"name": "Participant Cria", "email": "partcria@test.com"}

        resp = client_participant.post("/api/users", json=payload)

        assert resp.status_code == 201


# ─── GET /users ──────────────────────────────────────────────────────────────
# Verificar acesso de MANAGER.
# Verificar restrição para PARTICIPANT.
# Verificar se tem outras questões de autorização no doc API


# ─── GET /users/{userId} ───────────────────────────────────────────────────
# Verificar acesso ao próprio usuário.
# Verificar acesso a usuários de terceiros.
# Verificar se tem outras questões de autorização no doc API


# ─── PATCH /users/{userId} ───────────────────────────────────────────────────
class TestAutorizacaoPatchUser:

    def test_sem_token_retorna_401(self, client, criar_usuario):
        """PATCH sem Authorization header deve retornar 401."""
        usuario = criar_usuario()

        resp = client.patch(
            f"/api/users/{usuario.id}",
            json={"name": "Sem Token"},
        )

        assert resp.status_code == 401

    def test_manager_pode_atualizar_qualquer_usuario(self, client_manager, criar_usuario):
        """
        MANAGER tem acesso irrestrito: pode atualizar qualquer usuário,
        mesmo sem relação de identidade com ele.
        """
        usuario = criar_usuario(email="terceiro@test.com")

        resp = client_manager.patch(
            f"/api/users/{usuario.id}",
            json={"name": "Atualizado pelo Manager"},
        )

        assert resp.status_code == 200

    def test_participant_pode_atualizar_o_proprio_usuario(
        self, client_participant, criar_usuario
    ):
        """
        PARTICIPANT pode atualizar somente sua própria conta.
        O e-mail do usuário criado deve ser igual ao do token (participant@test.com).
        """
        usuario = criar_usuario(
            email="participant@test.com",  # mesmo e-mail do PARTICIPANT_PAYLOAD
        )

        resp = client_participant.patch(
            f"/api/users/{usuario.id}",
            json={"name": "Atualizado pelo próprio"},
        )

        assert resp.status_code == 200

    def test_participant_nao_pode_atualizar_usuario_de_terceiro_retorna_403(
        self, client_participant, criar_usuario
    ):
        """
        PARTICIPANT não pode atualizar conta de outro usuário.
        O e-mail do alvo é diferente do token → deve retornar 403.
        """
        usuario = criar_usuario(
            email="outro@test.com",  # e-mail DIFERENTE do token (participant@test.com)
        )

        resp = client_participant.patch(
            f"/api/users/{usuario.id}",
            json={"name": "Tentativa indevida"},
        )

        assert resp.status_code == 403


# ─── DELETE /users/{userId} ───────────────────────────────────────────────────
class TestAutorizacaoDeleteUser:

    def test_sem_token_retorna_401(self, client, criar_usuario):
        """DELETE sem Authorization header deve retornar 401."""
        usuario = criar_usuario()

        resp = client.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Sem autenticação"},
        )

        assert resp.status_code == 401

    def test_manager_pode_desativar_qualquer_usuario(self, client_manager, criar_usuario):
        """
        MANAGER tem acesso irrestrito: pode desativar qualquer usuário,
        mesmo sem relação de identidade com ele.
        """
        usuario = criar_usuario(email="terceiro@test.com", status="ACTIVE")

        resp = client_manager.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Decisão do gestor"},
        )

        assert resp.status_code == 200

    def test_participant_pode_desativar_o_proprio_usuario(
        self, client_participant, criar_usuario
    ):
        """
        PARTICIPANT pode desativar somente sua própria conta.
        O e-mail do usuário criado deve ser igual ao do token (participant@test.com).
        """
        usuario = criar_usuario(
            email="participant@test.com",  # mesmo e-mail do PARTICIPANT_PAYLOAD
            status="ACTIVE",
        )

        resp = client_participant.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Saindo voluntariamente"},
        )

        assert resp.status_code == 200

    def test_participant_nao_pode_desativar_usuario_de_terceiro_retorna_403(
        self, client_participant, criar_usuario
    ):
        """
        PARTICIPANT não pode desativar conta de outro usuário.
        O e-mail do alvo é diferente do token → deve retornar 403.
        """
        usuario = criar_usuario(
            email="outro@test.com",  # e-mail DIFERENTE do token (participant@test.com)
            status="ACTIVE",
        )

        resp = client_participant.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Tentativa indevida"},
        )

        assert resp.status_code == 403

# ─── PUT /users/{userId}/roles ───────────────────────────────────────────────
# Verificar quem pode alterar papéis.
# Verificar se tem outras questões de autorização no doc API

