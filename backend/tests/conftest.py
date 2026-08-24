"""
Fixtures compartilhadas dos testes.

Cada teste roda contra um SQLite em memória isolado — criado do zero a
partir do Base.metadata (não das migrations), e descartado ao final do
teste. Isso mantém os testes rápidos e sem efeito colateral entre si.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app import models  # noqa: F401  (necessário para popular Base.metadata)
from app.main import app


@pytest.fixture()
def db_session():
    # StaticPool: mantém uma única conexão compartilhada para este engine.
    # Necessário porque SQLite `:memory:` é isolado por conexão — sem isso,
    # o TestClient (que roda os endpoints em outra thread via threadpool)
    # enxergaria um banco vazio diferente do criado aqui.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """
    TestClient da API com a dependência get_db substituída pela sessão
    isolada em memória de `db_session` — cada teste bate num banco próprio.
    """

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
