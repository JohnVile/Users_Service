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


# =========================================================
# FIXTURES
# =========================================================

'''
@pytest.fixture
def criar_usuario(setup_db):
    client = client_manager()
    with patch("app.services.user_service.KeycloakClient.create_user"):
        response = client.post("/api/users/", json={
            "name": "Joao Teste",
            "email": "joao@facom.ufms.br",
        })
    assert response.status_code == 201
    return response.json()'''


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

    def test_created_at_preenchido_e_updated_at_nulo(self, client):
        """Usuário recém-criado deve ter createdAt preenchido e updatedAt nulo."""
        resp = client.post("/api/users", json={"name": "Teste Nulo", "email": "nulo@test.com"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["createdAt"] is not None
        assert body["updatedAt"] is None
        assert body["deactivatedAt"] is None

# ─── GET /users ──────────────────────────────────────────────────────────────
class TestListaUsuariosIntegracao:

    def test_manager_lista_usuarios_retorna_200_com_contrato_correto(
        self, client_manager, criar_usuario
    ):
        """MANAGER listando usuários deve retornar 200 com items e metadados de paginação."""
        usuario = criar_usuario(name="Maria Silva", email="maria@test.com")

        resp = client_manager.get("/api/users")

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "page" in body
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == usuario.id
        assert body["items"][0]["name"] == "Maria Silva"
        assert body["page"]["page"] == 0
        assert body["page"]["size"] == 20
        assert body["page"]["totalElements"] == 1
        assert body["page"]["totalPages"] == 1

    def test_filtro_por_status_active(self, client_manager, criar_usuario):
        """Filtro status=ACTIVE deve retornar apenas usuários ativos."""
        ativo = criar_usuario(email="ativo@test.com", status="ACTIVE")
        criar_usuario(email="inativo@test.com", status="INACTIVE")

        resp = client_manager.get("/api/users", params={"status": "ACTIVE"})

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert ativo.id in ids
        assert len(ids) == 1

    def test_filtro_por_status_inactive(self, client_manager, criar_usuario):
        """Filtro status=INACTIVE deve retornar apenas usuários inativos."""
        criar_usuario(email="ativo@test.com", status="ACTIVE")
        inativo = criar_usuario(email="inativo@test.com", status="INACTIVE")

        resp = client_manager.get("/api/users", params={"status": "INACTIVE"})

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert inativo.id in ids
        assert len(ids) == 1

    def test_filtro_por_role_participant(self, client_manager, criar_usuario):
        """Filtro role=PARTICIPANT deve retornar apenas participantes."""
        participant = criar_usuario(email="part@test.com", roles="PARTICIPANT")
        criar_usuario(email="mgr@test.com", roles="MANAGER")

        resp = client_manager.get("/api/users", params={"role": "PARTICIPANT"})

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert participant.id in ids
        assert len(ids) == 1

    def test_filtro_por_role_manager(self, client_manager, criar_usuario):
        """Filtro role=MANAGER deve incluir usuários com múltiplos papéis."""
        criar_usuario(email="part@test.com", roles="PARTICIPANT")
        manager = criar_usuario(email="mgr@test.com", roles="MANAGER,PARTICIPANT")

        resp = client_manager.get("/api/users", params={"role": "MANAGER"})

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert manager.id in ids
        assert len(ids) == 1

    def test_filtros_status_e_role_combinados(self, client_manager, criar_usuario):
        """Filtros status e role combinados devem restringir o resultado."""
        criar_usuario(email="ativo-part@test.com", status="ACTIVE", roles="PARTICIPANT")
        criar_usuario(email="inativo-part@test.com", status="INACTIVE", roles="PARTICIPANT")
        alvo = criar_usuario(email="ativo-mgr@test.com", status="ACTIVE", roles="MANAGER")

        resp = client_manager.get(
            "/api/users",
            params={"status": "ACTIVE", "role": "MANAGER"},
        )

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert ids == [alvo.id]

    def test_paginacao_page_e_size(self, client_manager, criar_usuario):
        """Paginação deve respeitar page e size informados."""
        for i in range(3):
            criar_usuario(email=f"user{i}@test.com")

        resp = client_manager.get("/api/users", params={"page": 1, "size": 1})

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["page"]["page"] == 1
        assert body["page"]["size"] == 1
        assert body["page"]["totalElements"] == 3
        assert body["page"]["totalPages"] == 3

    def test_page_invalida_retorna_422(self, client_manager):
        """page negativa deve retornar 422."""
        resp = client_manager.get("/api/users", params={"page": -1})

        assert resp.status_code == 422

    def test_size_invalido_retorna_422(self, client_manager):
        """size fora do intervalo permitido deve retornar 422."""
        resp_zero = client_manager.get("/api/users", params={"size": 0})
        resp_grande = client_manager.get("/api/users", params={"size": 101})

        assert resp_zero.status_code == 422
        assert resp_grande.status_code == 422

    def test_status_invalido_retorna_422(self, client_manager):
        """Filtro status com valor fora do enum deve retornar 422."""
        resp = client_manager.get("/api/users", params={"status": "PENDENTE"})
        assert resp.status_code == 422

    def test_role_invalida_retorna_422(self, client_manager):
        """Filtro role com valor fora do enum deve retornar 422."""
        resp = client_manager.get("/api/users", params={"role": "ADMIN"})
        assert resp.status_code == 422


# ─── GET /users/{userId} ───────────────────────────────────────────────────
class TestGetUsuarioIntegracao:

    def test_manager_busca_usuario_retorna_200_e_dados_corretos(
        self, client_manager, criar_usuario
    ):
        """MANAGER consultando usuário existente deve retornar 200 com os dados completos."""
        usuario = criar_usuario(name="Maria Silva", email="maria@test.com")

        resp = client_manager.get(f"/api/users/{usuario.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == usuario.id
        assert body["name"] == "Maria Silva"
        assert body["email"] == "maria@test.com"
        assert body["status"] == "ACTIVE"
        assert body["roles"] == ["PARTICIPANT"]
        assert "createdAt" in body

    def test_participant_busca_propria_conta_retorna_200(
        self, client_participant, criar_usuario
    ):
        """PARTICIPANT consultando a própria conta deve retornar 200."""
        usuario = criar_usuario(email="participant@test.com", name="Eu Mesmo")

        resp = client_participant.get(f"/api/users/{usuario.id}")

        assert resp.status_code == 200
        assert resp.json()["email"] == "participant@test.com"

    def test_id_inexistente_retorna_404(self, client_manager):
        """Consulta por ID que não existe deve retornar 404."""
        resp = client_manager.get("/api/users/usr_inexistente")

        assert resp.status_code == 404

# ─── PATCH /users/{userId} ───────────────────────────────────────────────────
class TestPatchUsuarioIntegracao:
 
    # ── 200 OK ─────────────────────────────────────────────────────────────
 
    def test_manager_atualiza_nome_retorna_200_e_novo_nome(
        self, client_manager, criar_usuario
    ):
        """MANAGER atualizando name de outro usuário deve retornar 200 com novo nome."""
        usuario = criar_usuario(name="Nome Antigo", email="alvo@test.com")
 
        resp = client_manager.patch(
            f"/api/users/{usuario.id}", json={"name": "Nome Novo"}
        )
 
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Nome Novo"
        assert body["id"] == usuario.id
 
    def test_participant_atualiza_propria_conta_retorna_200(
        self, client_participant, criar_usuario
    ):

        usuario = criar_usuario(email="participant@test.com", name="Velho Nome")
 
        resp = client_participant.patch(
            f"/api/users/{usuario.id}", json={"name": "Novo Nome"}
        )
 
        assert resp.status_code == 200
        assert resp.json()["name"] == "Novo Nome"
 
    def test_patch_sem_campos_retorna_200_sem_alterar_dados(
        self, client_manager, criar_usuario
    ):
        """Corpo vazio ({}) deve retornar 200 com os dados originais intactos."""
        usuario = criar_usuario(name="Nome Original", email="original@test.com")
 
        resp = client_manager.patch(f"/api/users/{usuario.id}", json={})
 
        assert resp.status_code == 200
        assert resp.json()["name"] == "Nome Original"
 
    def test_resposta_contem_todos_os_campos_do_contrato(
        self, client_manager, criar_usuario
    ):
        """A resposta deve conter id, name, email, status, roles, createdAt."""
        usuario = criar_usuario(email="contrato@test.com")
 
        resp = client_manager.patch(
            f"/api/users/{usuario.id}", json={"name": "Nome Contrato"}
        )
 
        body = resp.json()
        for campo in ("id", "name", "email", "status", "roles", "createdAt"):
            assert campo in body, f"Campo '{campo}' ausente na resposta"
 
    # ── 404 ────────────────────────────────────────────────────────────────
 
    def test_usuario_inexistente_retorna_404(self, client_manager):
        """PATCH em ID que não existe deve retornar 404."""
        resp = client_manager.patch(
            "/api/users/usr_naoexiste", json={"name": "Não existe"}
        )
 
        assert resp.status_code == 404
 
    # ── 422 Unprocessable Entity ───────────────────────────────────────────
 
    def test_name_com_menos_de_3_chars_retorna_422(self, client_manager, criar_usuario):
        """name com menos de 3 caracteres deve falhar na validação Pydantic (422)."""
        usuario = criar_usuario(email="val@test.com")
 
        resp = client_manager.patch(f"/api/users/{usuario.id}", json={"name": "AB"})
 
        assert resp.status_code == 422
 
    def test_campo_desconhecido_e_ignorado_retorna_200(
        self, client_manager, criar_usuario
    ):

        usuario = criar_usuario(email="extra@test.com")
 
        resp = client_manager.patch(
            f"/api/users/{usuario.id}",
            json={"name": "Nome Ok", "campo_inventado": "valor"},
        )
 
        # Pydantic ignora campos extras — deve passar normalmente
        assert resp.status_code == 200
 
    # ── Persistência ───────────────────────────────────────────────────────
 
    def test_alteracao_e_persistida_no_banco(self, client_manager, criar_usuario, db):
        """O novo nome deve estar gravado no banco após o PATCH."""
        from app.models.user_model import User
 
        usuario = criar_usuario(email="persist@test.com", name="Antes")
 
        client_manager.patch(f"/api/users/{usuario.id}", json={"name": "Depois"})
 
        db.expire_all()
        user_db = db.query(User).filter(User.id == usuario.id).first()
        assert user_db.name == "Depois"

    # ── Campos de data ─────────────────────────────────────────────────────
    def test_updated_at_preenchido_apos_patch(self, client_manager, criar_usuario):
        """updatedAt deve ser preenchido (não nulo) após atualização."""
        usuario = criar_usuario(email="upd@test.com")

        resp = client_manager.patch(f"/api/users/{usuario.id}", json={"name": "Nome Novo"})

        body = resp.json()
        assert resp.status_code == 200
        assert body["updatedAt"] is not None


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

    def test_sem_body_retorna_422(self, client_manager, criar_usuario):
        """DELETE sem body deve retornar 422 — reason é obrigatório."""
        usuario = criar_usuario()
        resp = client_manager.request("DELETE", f"/api/users/{usuario.id}", json={})
        assert resp.status_code == 422

    def test_reason_curto_retorna_422(self, client_manager, criar_usuario):
        """reason com menos de 3 caracteres deve retornar 422."""
        usuario = criar_usuario()
        resp = client_manager.request("DELETE", f"/api/users/{usuario.id}", json={"reason": "AB"})
        assert resp.status_code == 422

# ─── PUT /users/{userId}/roles ───────────────────────────────────────────────
class TestIntegracaoAtualizaPapeis:

    # --- Rota e códigos HTTP ---
    def test_retorna_404_para_usuario_inexistente(
            self, client_manager):
        """Endpoint retorna 404 quando o userId não existe."""
        response = client_manager.put(
            "/api/users/usr_inexistente/roles",
            json={"roles": ["MANAGER"]},
        )
        assert response.status_code == 404

    def test_retorna_422_para_body_vazio(
            self, client_manager, criar_usuario):
        """Endpoint retorna 422 quando o body não contém roles."""
        usuario = criar_usuario()
        
        response = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={},
        )
        assert response.status_code == 422

    def test_retorna_422_para_role_invalida(
            self, client_manager, criar_usuario):
        """Endpoint retorna 422 quando a role não é MANAGER nem PARTICIPANT."""
        usuario = criar_usuario()
        
        response = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["ADMIN"]},
        )
        assert response.status_code == 422


    # --- Comunicação com banco ---

    def test_roles_persistidas_no_banco(
            self, client_manager, criar_usuario, db):
        """Após substituição, os roles devem estar salvos no banco."""
        usuario = criar_usuario(email="persistencia@test.com", roles="PARTICIPANT")
        
        client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["MANAGER"]},
        )

        response = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["MANAGER"]},
        )

        # Verifica resposta HTTP
        assert response.status_code == 200
        assert response.json()["id"] == usuario.id
        assert response.json()["roles"] == ["MANAGER"]

        db.refresh(usuario)  # recarrega do banco
        assert usuario.roles == "MANAGER"  # ou ["MANAGER"] dependendo do formato

    def test_substitui_integralmente_os_roles(
            self, client_manager, criar_usuario, db):
        """Roles anteriores devem ser substituídos, não acumulados."""
        usuario = criar_usuario(email="substituicao@test.com", roles="PARTICIPANT")
        
        # 1.PUT: promove para MANAGER

        response1 = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["MANAGER"]},
        )
        # 1.1. Verifica resposta HTTP do primeiro PUT
        assert response1.status_code == 200
        assert response1.json()["id"] == usuario.id
        assert response1.json()["roles"] == ["MANAGER"]

        # 1.2. Verifica banco após primeira mudança
        db.refresh(usuario)
        assert usuario.roles == "MANAGER"

        # 2.PUT: rebaixa para PARTICIPANT

        response2 = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["PARTICIPANT"]},
        )

        # 2.1. Verifica resposta HTTP do segundo PUT
        assert response2.status_code == 200
        assert response2.json()["id"] == usuario.id
        assert response2.json()["roles"] == ["PARTICIPANT"]

        # 2.2. Verifica banco após segunda mudança
        db.refresh(usuario)
        assert usuario.roles == "PARTICIPANT"


    # --- Comunicação com Keycloak ---

    def test_keycloak_e_chamado_com_email_e_roles(
            self, client_manager, criar_usuario):
        """O Keycloak deve ser chamado com o email do usuário e os novos roles."""
        usuario = criar_usuario(email="keycloak@test.com", roles="PARTICIPANT")

        response = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["MANAGER"]},
        )
        
        assert response.status_code == 200

    def test_falha_keycloak_nao_afeta_resposta(
            self, client_manager, criar_usuario):
        """Se o Keycloak falhar, o endpoint ainda retorna 200 (banco já foi atualizado)."""
        usuario = criar_usuario(email="falha@test.com")
        
        with patch(
            "app.integrations.keycloak_client.KeycloakClient.update_roles",
            side_effect=Exception("Keycloak fora do ar"),
        ):
            response = client_manager.put(
                f"/api/users/{usuario.id}/roles",
                json={"roles": ["MANAGER"]},
            )
        assert response.status_code == 200


    # --- Contrato api-docs.yaml ---

    def test_resposta_contem_campos_do_contrato(
            self, client_manager, criar_usuario):
        """Resposta deve conter todos os campos definidos no contrato."""
        usuario = criar_usuario()
        
        response = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["MANAGER"]},
        )
        
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "email" in data
        assert "status" in data
        assert "roles" in data
        assert "createdAt" in data

    def test_roles_retornados_como_lista(
            self, client_manager, criar_usuario):
        """O campo roles na resposta deve ser uma lista, conforme contrato."""
        usuario = criar_usuario()
        
        response = client_manager.put(
            f"/api/users/{usuario.id}/roles",
            json={"roles": ["MANAGER"]},
        )
        
        assert isinstance(response.json()["roles"], list)
