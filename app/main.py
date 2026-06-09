from fastapi import FastAPI

from app.core.database import Base, engine
from app.routes.user_routes import router as user_router

# Cria as tabelas no PostgreSQL na inicialização
# Para produção, prefira migrações via Alembic
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FACOFFEE Users Service",
    version="1.0.0",
    description="Microserviço de usuários da plataforma FACOFFEE.",
    response_model_by_alias=True,
)

# Rotas registradas sob /api/users
# Acesso via Gateway:  http://localhost:8000/api/users
# Acesso direto:       http://localhost:3001/api/users
# Swagger UI:          http://localhost:3001/docs
app.include_router(user_router, prefix="/api")
