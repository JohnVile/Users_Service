"""
TESTES DE INTEGRAÇÃO

Finalidade:
Validar o funcionamento completo dos endpoints.

Os testes devem verificar:
- Rotas
- Códigos HTTP
- Comunicação com banco
- Comunicação com Keycloak (quando aplicável)
- Contrato definido na api-docs.yaml
"""

import pytest
from unittest.mock import patch

# ─── POST /users ─────────────────────────────────────────────────────────────
class TestPostUsers:

    def test_criacao_retorna_201_e_campos_corretos(self, client):
        """Criação com dados válidos retorna 201 e o objeto User completo."""
        payload = {"name": "Maria Silva", "email": "maria@test.com", "roles": ["PARTICIPANT"]}

        resp = client.post("/api/users", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Maria Silva"
        assert body["email"] == "maria@test.com"
        assert body["status"] == "ACTIVE"
        assert body["roles"] == ["PARTICIPANT"]
        assert "id" in body
        assert body["id"].startswith("usr_")
        assert "createdAt" in body

    def test_sem_roles_usa_participant_por_padrao(self, client):
        """Quando roles não é enviado, o usuário é criado com PARTICIPANT."""
        payload = {"name": "João Costa", "email": "joao@test.com"}

        resp = client.post("/api/users", json=payload)

        assert resp.status_code == 201
        assert resp.json()["roles"] == ["PARTICIPANT"]

    def test_email_duplicado_retorna_409(self, client):
        """Segundo cadastro com o mesmo email deve retornar 409."""
        payload = {"name": "Teste", "email": "dup@test.com"}

        client.post("/api/users", json=payload)  # primeiro cadastro
        resp = client.post("/api/users", json=payload)  # duplicado

        assert resp.status_code == 409

    def test_email_invalido_retorna_422(self, client):
        """Email com formato inválido deve retornar 422 (validação Pydantic)."""
        payload = {"name": "Teste", "email": "nao-e-email"}

        resp = client.post("/api/users", json=payload)

        assert resp.status_code == 422

    def test_nome_com_menos_de_3_caracteres_retorna_422(self, client):
        """Nome menor que 3 caracteres deve retornar 422 (minLength do schema)."""
        payload = {"name": "AB", "email": "teste@test.com"}

        resp = client.post("/api/users", json=payload)

        assert resp.status_code == 422

    def test_campos_obrigatorios_ausentes_retornam_422(self, client):
        """Corpo sem 'name' e 'email' deve retornar 422."""
        resp = client.post("/api/users", json={})

        assert resp.status_code == 422


# ─── GET /users ──────────────────────────────────────────────────────────────
# Testar listagem, filtros e paginação.


# ─── GET /users/{userId} ───────────────────────────────────────────────────
# Testar busca de usuário por identificador.


# ─── PATCH /users/{userId} ───────────────────────────────────────────────────
# Testar atualização completa de usuário.


# ─── DELETE /users/{userId} ───────────────────────────────────────────────────
class TestDeleteUser:

    def test_manager_desativa_usuario_retorna_200_e_status_inactive(
        self, client_manager, criar_usuario
    ):
        """MANAGER desativando usuário existente retorna 200 com status INACTIVE."""
        usuario = criar_usuario(email="alvo@test.com", status="ACTIVE")

        resp = client_manager.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Solicitação do gestor"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "INACTIVE"
        assert body["id"] == usuario.id
        assert "deactivatedAt" in body

    def test_usuario_inexistente_retorna_404(self, client_manager):
        """Tentar desativar ID que não existe deve retornar 404."""
        resp = client_manager.request(
            "DELETE",
            "/api/users/usr_naoexiste",
            json={"reason": "Motivo qualquer"},
        )

        assert resp.status_code == 404

    def test_usuario_ja_inativo_retorna_409(self, client_manager, criar_usuario):
        """Tentar desativar usuário que já é INACTIVE deve retornar 409."""
        usuario = criar_usuario(email="inativo@test.com", status="INACTIVE")

        resp = client_manager.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Já estava inativo"},
        )

        assert resp.status_code == 409

    def test_sem_autenticacao_retorna_401(self, client, criar_usuario):
        """Requisição sem token JWT deve retornar 401."""
        usuario = criar_usuario()

        resp = client.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Sem token"},
        )

        assert resp.status_code == 401

    def test_participant_desativa_a_propria_conta_retorna_200(
        self, client_participant, criar_usuario
    ):
        """
        PARTICIPANT pode desativar o próprio usuário.
        O email do usuário no banco deve coincidir com o email do token
        (participant@test.com — definido em PARTICIPANT_PAYLOAD no conftest).
        """
        usuario = criar_usuario(email="participant@test.com", status="ACTIVE")

        resp = client_participant.request(
            "DELETE",
            f"/api/users/{usuario.id}",
            json={"reason": "Saindo da plataforma"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "INACTIVE"

    def test_evento_rabbitmq_e_publicado(self, client_manager, criar_usuario):
        """O evento UserDeactivated deve ser publicado ao desativar com sucesso."""
        usuario = criar_usuario(email="evento@test.com", status="ACTIVE")

        with patch(
            "app.integrations.rabbitmq_client.RabbitMQClient.publish_user_deactivated"
        ) as mock_publish:
            client_manager.request(
                "DELETE",
                f"/api/users/{usuario.id}",
                json={"reason": "Motivo do evento"},
            )
            mock_publish.assert_called_once_with(usuario.id, "Motivo do evento")


# ─── PUT /users/{userId}/roles ───────────────────────────────────────────────
# Testar substituição de papéis.
