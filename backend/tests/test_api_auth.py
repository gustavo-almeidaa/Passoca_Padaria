"""Testes de integração da autenticação — Incremento 12."""
from app.core.security import hash_senha
from app.models.usuario import PerfilUsuario, Usuario


def _criar_usuario(
    db_session,
    nome="Proprietária Teste",
    email="dona@passoca.com",
    senha="senha-valida-123",
    perfil=PerfilUsuario.PROPRIETARIA,
    ativo=True,
):
    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=hash_senha(senha),
        perfil=perfil,
        ativo=ativo,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


class TestLogin:
    def test_login_com_credenciais_corretas(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")

        resp = client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-valida-123"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "dona@passoca.com"
        assert "senha" not in data
        assert "senha_hash" not in data

    def test_login_com_senha_errada_e_rejeitado(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")

        resp = client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-errada"}
        )

        assert resp.status_code == 401

    def test_login_com_email_inexistente_e_rejeitado(self, client_anonimo):
        resp = client_anonimo.post(
            "/auth/login", json={"email": "ninguem@passoca.com", "senha": "qualquer-senha"}
        )

        assert resp.status_code == 401

    def test_login_de_usuario_inativo_e_rejeitado(self, client_anonimo, db_session):
        _criar_usuario(
            db_session, email="ex-funcionaria@passoca.com", senha="senha-valida-123", ativo=False
        )

        resp = client_anonimo.post(
            "/auth/login",
            json={"email": "ex-funcionaria@passoca.com", "senha": "senha-valida-123"},
        )

        assert resp.status_code == 401


class TestMe:
    def test_me_sem_sessao_retorna_401(self, client_anonimo):
        resp = client_anonimo.get("/auth/me")

        assert resp.status_code == 401

    def test_me_com_sessao_valida_retorna_usuario(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-valida-123"}
        )

        resp = client_anonimo.get("/auth/me")

        assert resp.status_code == 200
        assert resp.json()["email"] == "dona@passoca.com"


class TestLogout:
    def test_logout_encerra_sessao(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-valida-123"}
        )

        resp_logout = client_anonimo.post("/auth/logout")
        resp_me = client_anonimo.get("/auth/me")

        assert resp_logout.status_code == 204
        assert resp_me.status_code == 401


class TestRotasProtegidas:
    def test_rota_de_negocio_sem_sessao_retorna_401(self, client_anonimo):
        resp = client_anonimo.get("/clientes")

        assert resp.status_code == 401

    def test_rota_de_negocio_com_sessao_funciona(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-valida-123"}
        )

        resp = client_anonimo.get("/clientes")

        assert resp.status_code == 200


class TestCriarUsuario:
    def test_criar_usuario_sem_sessao_e_rejeitado(self, client_anonimo):
        resp = client_anonimo.post(
            "/auth/usuarios",
            json={
                "nome": "Atendente Nova",
                "email": "atendente@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "atendente",
            },
        )

        assert resp.status_code == 401

    def test_criar_usuario_autenticado_funciona(self, client):
        resp = client.post(
            "/auth/usuarios",
            json={
                "nome": "Atendente Nova",
                "email": "atendente@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "atendente",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["perfil"] == "atendente"
        assert "senha_hash" not in data

    def test_criar_usuario_com_email_duplicado_e_rejeitado(self, client):
        payload = {
            "nome": "Atendente Nova",
            "email": "atendente@passoca.com",
            "senha": "senha-valida-123",
            "perfil": "atendente",
        }
        client.post("/auth/usuarios", json=payload)

        resp = client.post("/auth/usuarios", json=payload)

        assert resp.status_code == 409

    def test_criar_usuario_com_senha_curta_e_rejeitado(self, client):
        resp = client.post(
            "/auth/usuarios",
            json={
                "nome": "Atendente Nova",
                "email": "atendente@passoca.com",
                "senha": "curta",
                "perfil": "atendente",
            },
        )

        assert resp.status_code == 422

    def test_listar_usuarios_inclui_usuario_autenticado(self, client, usuario_teste):
        resp = client.get("/auth/usuarios")

        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert usuario_teste.email in emails
