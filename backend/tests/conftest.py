"""
Fixtures compartilhadas dos testes.

Por padrão cada teste roda contra um SQLite em memória isolado — criado do
zero a partir do `Base.metadata` (não das migrations) e descartado ao
final. Rápido e sem efeito colateral entre testes.

Incremento 21 (auditoria A-04): se `TEST_DATABASE_URL` estiver setada
(ex.: `postgresql+psycopg://...` no CI), a suíte roda contra esse banco
real em vez do SQLite — mesma lógica de "schema do zero por teste", só que
no motor de produção. Assim `CHECK` constraint, tipo `Numeric`, enums
não-nativos e semântica transacional são exercidos como em produção.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app import models  # noqa: F401  (necessário para popular Base.metadata)
from app.api.deps import get_usuario_atual
from app.core.database import Base, get_db
from app.core.security import hash_senha
from app.main import app
from app.models.usuario import PerfilUsuario, Usuario

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _criar_engine():
    if TEST_DATABASE_URL:
        # Banco real (CI). NullPool: cada teste abre/fecha sua conexão, sem
        # pool sobrevivendo entre testes.
        return create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    # StaticPool: mantém uma única conexão compartilhada para este engine.
    # Necessário porque SQLite `:memory:` é isolado por conexão — sem isso,
    # o TestClient (que roda os endpoints em outra thread via threadpool)
    # enxergaria um banco vazio diferente do criado aqui.
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture()
def db_session():
    engine = _criar_engine()
    # drop antes do create cobre o caso de um teste anterior ter deixado
    # tabela pra trás no Postgres (no SQLite `:memory:` fresco é no-op).
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def usuario_teste(db_session):
    """Usuário autenticado padrão pros testes de RF01-RF07 — não testa login
    em si (isso é o `test_api_auth.py`, com `client_anonimo`), só precisa
    de *algum* usuário válido pra passar pela dependência de autenticação.
    """
    usuario = Usuario(
        nome="Usuária de Teste",
        email="teste@passoca.com",
        senha_hash=hash_senha("senha-de-teste-123"),
        perfil=PerfilUsuario.PROPRIETARIA,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


def _test_client(db_session):
    # Sem `with`: propositalmente não dispara o lifespan da app (ver
    # app/main.py) — o bootstrap do usuário inicial usa a conexão real
    # (Neon), não a `db_session` isolada daqui, e não deve rodar durante
    # os testes.
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    return TestClient(app)


@pytest.fixture()
def client(db_session, usuario_teste):
    """TestClient com banco isolado *e* usuário já autenticado — é o que a
    maioria dos testes (RF01-RF07) deve usar, já que a rota em si não é o
    que está sendo testado.
    """

    def _get_usuario_atual_override():
        return usuario_teste

    app.dependency_overrides[get_usuario_atual] = _get_usuario_atual_override
    try:
        yield _test_client(db_session)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def client_anonimo(db_session):
    """TestClient com banco isolado, sem override de autenticação — pros
    testes do próprio módulo de auth (login, logout, rota protegida sem
    sessão), que precisam do fluxo real.
    """
    try:
        yield _test_client(db_session)
    finally:
        app.dependency_overrides.clear()
