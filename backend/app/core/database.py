"""
Conexão com o banco de dados.

Mantido agnóstico de banco de propósito: tudo passa pela DATABASE_URL e pelo
SQLAlchemy ORM, sem SQL específico de SQLite espalhado pelo código. Isso
facilita uma futura migração manual para PostgreSQL (troca a URL + roda as
migrations do Alembic no banco novo).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# connect_args com check_same_thread só é necessário pro SQLite (o FastAPI
# usa múltiplas threads pra servir requisições). Em Postgres esse dict fica
# vazio automaticamente.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe base declarativa — todos os models herdam daqui."""
    pass


def get_db():
    """Dependency do FastAPI: abre uma sessão por requisição e sempre fecha."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
