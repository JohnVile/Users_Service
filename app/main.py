from fastapi import FastAPI
from app.core.database import Base
from app.core.database import engine
from app.routes.user_routes import router as user_router

# Cria automaticamente as tabelas no PostgreSQL

Base.metadata.create_all(bind=engine)

# Cria a instância principal da aplicação
app = FastAPI(
    title="FACOFFEE Users Service",
    version="1.0.0"
)

# Ativa e injeta as rotas de usuário na aplicação principal
app.include_router(user_router)

