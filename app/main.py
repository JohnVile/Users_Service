from fastapi import FastAPI
from app.core.database import Base
from app.core.database import engine
from app.routes.user_routes import router as user_router

# Cria automaticamente as tabelas no PostgreSQL

Base.metadata.create_all(bind=engine)

# Cria a instância principal da aplicação
app = FastAPI(
    title="FACOFFEE Users Service",
    version="1.0.0",
    response_model_by_alias=True,
)

# /users  -> testes diretos na porta 3001
# /api/users -> chamadas via gateway (http://localhost:8000/api/users)
app.include_router(user_router)
app.include_router(user_router, prefix="/api")

