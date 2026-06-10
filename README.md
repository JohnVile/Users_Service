# Users Service — FACOFFEE

Microserviço de usuários da plataforma FACOFFEE.
Desenvolvido com Python + FastAPI + PostgreSQL + Docker.

## Equipe

* Enzo Euvine Cunha Neves
* João Vitor Costa Braga
* Louise Mayumi Takigawa Pereira
* Mateus Miranda Seron

---

## Pré-requisitos

* Docker 24+ e Docker Compose v2+
* A infra do professor (`facoffee-docs`) rodando
* DBeaver: Para visualizar o banco (Opcional)

---

## 0. Instalação de serviços essenciais

* Baixe o Docker Compose para Desktop (<https://www.docker.com/get-started/>)
* Instale via terminal o Curl para uso de testes da API (Windows): `winget install cURL.cURL`
* Baixe o DBheaver para visualizar o banco PostgreSQL (<https://dbeaver.io/download/>)

### Configurações do DBeaver

| Campo | Valor |
| -------- | -------- |
| Host | localhost |
| Porta | 5432 |
| Database | `users_db` |
| Usuário | `admin` |
| Senha | `admin` |

## 1. Suba a infra do professor

```bash
cd facoffee-docs
docker compose up -d
```

Aguarde ~30s até o Keycloak estar disponível em <http://localhost:8080>.

Para confirmar:

```bash
docker compose ps
```

---

## 2. Suba o Users Service

```bash
cd Users_Service
docker compose up -d --build
```

Confirme que está rodando:

```bash
docker compose ps
docker compose logs users-service
```

A API fica disponível em:

* **Via Gateway (recomendado):** `http://localhost:8000/api/users`
* **Direto no serviço:** `http://localhost:3001/users`
* **Swagger:** `http://localhost:3001/docs`

---

## 2.1 Como rodar os testes automatizados?

Dentro de Users_Service/

```bash
python -m pytest -v
```

Com relatório de cobertura:

```bash
python -m pytest -v --cov=app --cov-report=term-missing
```

Gerar evidência em arquivo:

```bash
python -m pytest -v > resultados_testes.txt 2>&1
```

Gerar evidência em HTML:

```bash
python -m pytest --html=relatorio.html
```

---

## 3. Testes manuais para a criação de usuário - `POST /users`

⚠️ Atenção: É possível testar usando o Git Bash ou o WSL

### Criar usuário (POST /users — sem token)

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Maria Silva", "email": "maria@facom.ufms.br"}'
```

Resposta esperada: `201 Created`

```json
{
  "id": 1,
  "name": "Maria Silva",
  "email": "maria@facom.ufms.br",
  "status": "ACTIVE",
  "roles": ["PARTICIPANT"],
  "created_at": "2026-01-01T00:00:00"
}
```

### Testar conflito de e-mail (409)

Envie o mesmo e-mail duas vezes. Resposta esperada: `409 Conflict`.

---

## 4. Obtendo token para testar endpoints protegidos

Todos os endpoints (exceto `POST /users`) exigem um token JWT no header:

```text
Authorization: Bearer <access_token>
```

### Tipos de token disponíveis

#### Token de usuário MANAGER (recomendado para testes)

Usa o usuário pré-configurado no realm `facoffee` com role `MANAGER`.
**Este é o token a ser usado na maioria dos testes.**

```bash
curl -X POST "http://localhost:8080/realms/facoffee/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=facoffee-public" \
  -d "username=facoffee@facom.ufms.br" \
  -d "password=facoffee"
```

Copie o valor do campo `access_token` da resposta. Exemplo de uso:

```bash
TOKEN="<cole o access_token aqui>"
```

#### Token de usuário PARTICIPANT (para testar controle de acesso)

Após criar um usuário via `POST /users`, acesse o painel do Keycloak:

1. Abra <http://localhost:8080> → Login: `facoffee` / `facoffee`
2. Selecione o realm **facoffee** (não o master)
3. Vá em **Users** → clique no usuário criado → aba **Credentials**
4. Clique em **Set password**, defina uma senha e desmarque "Temporary"

Depois, obtenha o token do PARTICIPANT:

```bash
curl -X POST "http://localhost:8080/realms/facoffee/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=facoffee-public" \
  -d "username=<email-do-usuario-criado>" \
  -d "password=<senha-que-voce-definiu>"
```

#### Token de serviço (uso interno do sistema)

O token `facoffee-private` com `client_credentials` é usado pelo próprio serviço
para chamar a API Admin do Keycloak (criar/atualizar usuários). **Não contém
roles de domínio (MANAGER/PARTICIPANT)** — não serve para testar endpoints de usuário.

```bash
curl -X POST "http://localhost:8080/realms/facoffee/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=facoffee-private" \
  -d "client_secret=facoffee-private-secret"
```

---

## 5. Testes para listar usuários — `GET /users`

### Listar usuários — `GET /users`

Retorna a lista paginada. Requer token de MANAGER.

```bash
curl -X GET "http://localhost:8000/api/users" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada: `200 OK`

```json
{
  "items": [
    {
      "id": "usr_a1b2c3d4e5f6",
      "name": "Maria Silva",
      "email": "maria@facom.ufms.br",
      "status": "ACTIVE",
      "roles": ["PARTICIPANT"],
      "createdAt": "2026-01-01T00:00:00Z",
      "updatedAt": null,
      "deactivatedAt": null
    }
  ],
  "page": {
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1
  }
}
```

### Listar com filtros (status e role)

```bash
curl -X GET "http://localhost:8000/api/users?status=ACTIVE&role=PARTICIPANT&page=0&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Testar acesso negado de PARTICIPANT ao listar (403)

Se você tiver um token de PARTICIPANT:

```bash
curl -X GET "http://localhost:8000/api/users" \
  -H "Authorization: Bearer $TOKEN_PARTICIPANT"
```

Resposta esperada: `403 Forbidden`

---

## 6. Testes para buscar usuário por ID — `GET /users/{userId}`

```bash
USER_ID="usr_a1b2c3d4e5f6"   # substitua pelo ID real

curl -X GET "http://localhost:8000/api/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada: `200 OK` com os dados do usuário.

### Buscar ID inexistente (404)

```bash
curl -X GET "http://localhost:8000/api/users/usr_inexistente" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta esperada: `404 Not Found`

---

## 7. Testes para atualizar nome do usuário — `PATCH /users/{userId}`

```bash
USER_ID="usr_a1b2c3d4e5f6"

curl -X PATCH "http://localhost:8000/api/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Maria Souza Silva"}'
```

Resposta esperada: `200 OK` com os dados atualizados.

---

## 8. Testes para substituir papéis do usuário — `PUT /users/{userId}/roles`

```bash
USER_ID="usr_a1b2c3d4e5f6"

curl -X PUT "http://localhost:8000/api/users/$USER_ID/roles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["MANAGER"]}'
```

Resposta esperada: `200 OK` com os dados atualizados.

Após o comando, verifique no painel do Keycloak:

1. <http://localhost:8080> → realm `facoffee` → **Users** → [usuário] → aba **Role mappings**
2. A role `MANAGER` deve aparecer em **Assigned roles**

---

## 9. Desativar usuário — `DELETE /users/{userId}`

```bash
USER_ID="usr_a1b2c3d4e5f6"

curl -X DELETE "http://localhost:8000/api/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Usuário não participa mais da copa"}'
```

Resposta esperada: `200 OK` com `"status": "INACTIVE"` e `"deactivatedAt"` preenchido.

### Testar desativar usuário já inativo (409)

Tente desativar o mesmo usuário novamente:

```bash
curl -X DELETE "http://localhost:8000/api/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Tentativa duplicada"}'
```

Resposta esperada: `409 Conflict`

---

## 10. Variáveis de ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql://admin:admin@db:5432/users_db` |
| `KEYCLOAK_URL` | URL base do Keycloak | `http://host.docker.internal:8080` |
| `KEYCLOAK_REALM` | Realm da aplicação | `facoffee` |
| `KEYCLOAK_CLIENT_ID` | Client ID confidencial | `facoffee-private` |
| `KEYCLOAK_CLIENT_SECRET` | Secret do client confidencial | `facoffee-private-secret` |
| `KEYCLOAK_ADMIN_USER` | Usuário admin do Keycloak | `facoffee` |
| `KEYCLOAK_ADMIN_PASSWORD` | Senha admin do Keycloak | `facoffee` |
| `RABBITMQ_HOST` | Host do RabbitMQ | `host.docker.internal` |
| `RABBITMQ_PORT` | Porta AMQP do RabbitMQ | `5672` |
| `RABBITMQ_USER` | Usuário do RabbitMQ | `facoffee` |
| `RABBITMQ_PASSWORD` | Senha do RabbitMQ | `facoffee` |
