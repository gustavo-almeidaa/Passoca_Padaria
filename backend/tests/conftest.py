"""
Fixtures compartilhadas dos testes.

Cada teste roda contra um SQLite em memória isolado — criado do zero a
partir do Base.metadata (não das migrations), e descartado ao final do
teste. Isso mantém os testes rápidos e sem efeito colateral entre si.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models  # noqa: F401  (necessário para popular Base.metadata)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
