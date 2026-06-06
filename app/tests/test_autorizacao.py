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

# Endpoint: POST /users
# Verificar quem pode criar usuários.


# Endpoint: GET /users
# Verificar acesso de MANAGER.
# Verificar restrição para PARTICIPANT.
# Verificar se tem outras questões de autorização no doc API


# Endpoint: GET /users/{userId}
# Verificar acesso ao próprio usuário.
# Verificar acesso a usuários de terceiros.
# Verificar se tem outras questões de autorização no doc API


# Endpoint: PATCH /users/{userId}
# Verificar permissões de atualização.
# Verificar se tem outras questões de autorização no doc API


# Endpoint: DELETE /users/{userId}
# Verificar permissões de desativação.
# Verificar se tem outras questões de autorização no doc API


# Endpoint: PUT /users/{userId}/roles
# Verificar quem pode alterar papéis.
# Verificar se tem outras questões de autorização no doc API

