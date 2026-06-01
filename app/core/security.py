"""
===========================================================
SEGURANÇA / AUTENTICAÇÃO / AUTORIZAÇÃO DO MICROSSERVIÇO
===========================================================

Este arquivo será responsável por controlar:

1. AUTENTICAÇÃO
   - validar JWT vindo do Keycloak
   - verificar se o token é válido
   - identificar qual usuário fez a requisição

2. AUTORIZAÇÃO
   - verificar permissões do usuário
   - validar roles (MANAGER / PARTICIPANT)
   - proteger endpoints da API

-----------------------------------------------------------
COMO ISSO FUNCIONA NO SISTEMA
-----------------------------------------------------------

Fluxo esperado:

Frontend/Postman
    ↓
Envia Bearer Token JWT
    ↓
FastAPI chama Depends()
    ↓
security.py valida token
    ↓
extrai usuário e roles
    ↓
permite ou bloqueia acesso
    ↓
rota executa

-----------------------------------------------------------
FUNÇÕES IMPORTANTES
-----------------------------------------------------------

get_current_user()
    - receber token JWT
    - validar token no Keycloak
    - extrair payload
    - retornar dados do usuário autenticado

Exemplo esperado:
{
    "sub": "123",
    "email": "enzo@gmail.com",
    "roles": ["MANAGER"]
}

-----------------------------------------------------------

require_manager()
    - permitir acesso apenas para MANAGER
    - usado em endpoints administrativos

Exemplo:
GET /users

-----------------------------------------------------------

require_self_or_manager()
    - permitir:
        - o próprio usuário
        - OU um manager
    - bloquear outros usuários

Exemplo:
GET /users/{id}

-----------------------------------------------------------
LIGAÇÃO COM O RESTO DO SISTEMA
-----------------------------------------------------------

Este arquivo será utilizado nas rotas:

routes/user_routes.py

Exemplo:

@router.get("/")
def list_users(
    current_user = Depends(require_manager)
):

-----------------------------------------------------------
INTEGRAÇÃO COM KEYCLOAK
-----------------------------------------------------------

Será necessário:

- validar assinatura do JWT
- validar issuer
- validar expiration
- extrair realm_access.roles
- extrair sub/email

Bibliotecas provavelmente utilizadas:
- python-jose
- requests
- fastapi.security

-----------------------------------------------------------
IMPORTANTE
-----------------------------------------------------------

Este arquivo é o "guardião" da API.

Toda regra de acesso centralizada aqui evita:
- código duplicado
- falhas de segurança
- validações espalhadas
- lógica repetida nas rotas

===========================================================
"""

from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()


def get_current_user():
    pass


def require_manager():
    pass


def require_self_or_manager():
    pass