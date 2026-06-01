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

##### Configurações do DBeaver:

| Campo | Valor |
|--------|--------|
| Host | localhost |
| Porta | 5432 |
| Database | `users_db` |
| Usuário | `admin` |
| Senha | `admin`

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

## 3. Testando a criação de usuário

⚠️ Atenção: É possível testar usando o Git Bash ou o WSL

### Criar usuário (POST /users — sem token)

```bash
curl -X POST http://localhost:3001/users/ \
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

### Via Gateway (Nginx)

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Maria Silva", "email": "maria@facom.ufms.br"}'
```

---

## 4. Obtendo token para testar outros endpoints

```bash
curl -X POST http://localhost:8080/realms/facoffee/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=facoffee-public" \
  -d "username=facoffee@facom.ufms.br" \
  -d "password=facoffee"
```

Use o `access_token` retornado no header:
