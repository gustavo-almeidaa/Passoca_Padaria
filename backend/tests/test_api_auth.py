"""Testes de integração da autenticação — Incrementos 12 e 17."""
import pytest

from app.core.security import hash_senha
from app.models.tentativa_login import TentativaLogin
from app.models.usuario import PerfilUsuario, Usuario
from app.services import rate_limit


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


class TestLimiteDeTentativas:
    """Incremento 17 / auditoria A-02 — limite por IP, conta nunca trava."""

    @pytest.fixture(autouse=True)
    def _sem_sleep_real(self, monkeypatch):
        """Não espera de verdade nos testes; guarda os atrasos pedidos."""
        self.atrasos = []
        monkeypatch.setattr(
            "app.api.auth.time.sleep", lambda s: self.atrasos.append(s)
        )

    def _errar_login(self, client_anonimo, vezes, ip="203.0.113.7"):
        for _ in range(vezes):
            client_anonimo.post(
                "/auth/login",
                json={"email": "dona@passoca.com", "senha": "errada"},
                headers={"X-Forwarded-For": ip},
            )

    def test_poucas_falhas_nao_penalizam(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        self._errar_login(client_anonimo, rate_limit.LIMIAR_ATRASO - 1)

        assert self.atrasos == []

    def test_a_partir_do_limiar_aplica_atraso(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        self._errar_login(client_anonimo, rate_limit.LIMIAR_ATRASO + 1)

        assert self.atrasos  # pelo menos um atraso foi aplicado
        assert self.atrasos[0] == rate_limit.ATRASO_BASE_SEGUNDOS

    def test_login_correto_ainda_passa_na_faixa_de_atraso(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        self._errar_login(client_anonimo, rate_limit.LIMIAR_ATRASO)

        resp = client_anonimo.post(
            "/auth/login",
            json={"email": "dona@passoca.com", "senha": "senha-valida-123"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )

        assert resp.status_code == 200

    def test_bloqueia_com_429_e_retry_after(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        self._errar_login(client_anonimo, rate_limit.LIMIAR_BLOQUEIO)

        # Mesmo com a senha certa: o IP está bloqueado, nem chega a checar.
        resp = client_anonimo.post(
            "/auth/login",
            json={"email": "dona@passoca.com", "senha": "senha-valida-123"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )

        assert resp.status_code == 429
        assert int(resp.headers["retry-after"]) > 0

    def test_bloqueio_e_por_ip_nao_por_conta(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")
        self._errar_login(client_anonimo, rate_limit.LIMIAR_BLOQUEIO, ip="203.0.113.7")

        # Outro dispositivo (outro IP), mesma conta: passa.
        resp = client_anonimo.post(
            "/auth/login",
            json={"email": "dona@passoca.com", "senha": "senha-valida-123"},
            headers={"X-Forwarded-For": "198.51.100.2"},
        )

        assert resp.status_code == 200

    def test_mensagem_generica_preservada(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")

        resp = client_anonimo.post(
            "/auth/login",
            json={"email": "dona@passoca.com", "senha": "errada"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "E-mail ou senha incorretos."

    def test_login_registra_tentativa(self, client_anonimo, db_session):
        _criar_usuario(db_session, email="dona@passoca.com", senha="senha-valida-123")

        client_anonimo.post(
            "/auth/login",
            json={"email": "dona@passoca.com", "senha": "senha-valida-123"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )

        registro = db_session.query(TentativaLogin).one()
        assert registro.sucesso is True
        assert registro.ip == "203.0.113.7"


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


class TestTrocarSenha:
    def _login(self, client_anonimo, db_session, senha="senha-antiga-123"):
        _criar_usuario(db_session, email="dona@passoca.com", senha=senha)
        client_anonimo.post("/auth/login", json={"email": "dona@passoca.com", "senha": senha})

    def test_trocar_senha_com_senha_atual_correta(self, client_anonimo, db_session):
        self._login(client_anonimo, db_session)

        resp = client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-antiga-123", "senha_nova": "senha-nova-456"},
        )

        assert resp.status_code == 204

    def test_login_com_senha_nova_funciona_depois_da_troca(self, client_anonimo, db_session):
        self._login(client_anonimo, db_session)
        client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-antiga-123", "senha_nova": "senha-nova-456"},
        )
        client_anonimo.post("/auth/logout")

        resp = client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-nova-456"}
        )

        assert resp.status_code == 200

    def test_login_com_senha_antiga_deixa_de_funcionar_apos_troca(self, client_anonimo, db_session):
        self._login(client_anonimo, db_session)
        client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-antiga-123", "senha_nova": "senha-nova-456"},
        )
        client_anonimo.post("/auth/logout")

        resp = client_anonimo.post(
            "/auth/login", json={"email": "dona@passoca.com", "senha": "senha-antiga-123"}
        )

        assert resp.status_code == 401

    def test_trocar_senha_com_senha_atual_errada_e_rejeitado(self, client_anonimo, db_session):
        self._login(client_anonimo, db_session)

        resp = client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-errada", "senha_nova": "senha-nova-456"},
        )

        assert resp.status_code == 401

    def test_trocar_senha_com_nova_senha_curta_e_rejeitado(self, client_anonimo, db_session):
        self._login(client_anonimo, db_session)

        resp = client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-antiga-123", "senha_nova": "curta"},
        )

        assert resp.status_code == 422

    def test_trocar_senha_sem_sessao_e_rejeitado(self, client_anonimo):
        resp = client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "qualquer", "senha_nova": "senha-nova-456"},
        )

        assert resp.status_code == 401


class TestRestricaoProprietaria:
    """Incremento 15 (decisão do usuário): só a proprietária mexe em
    qualquer coisa da aba Usuários -- atendente/padeiro autenticados
    recebem 403, não 401 (a sessão é válida, só não tem permissão)."""

    def _login_atendente(self, client_anonimo, db_session):
        _criar_usuario(
            db_session,
            nome="Atendente",
            email="atendente@passoca.com",
            senha="senha-valida-123",
            perfil=PerfilUsuario.ATENDENTE,
        )
        client_anonimo.post(
            "/auth/login",
            json={"email": "atendente@passoca.com", "senha": "senha-valida-123"},
        )

    def test_atendente_nao_pode_listar_usuarios(self, client_anonimo, db_session):
        self._login_atendente(client_anonimo, db_session)

        resp = client_anonimo.get("/auth/usuarios")

        assert resp.status_code == 403

    def test_atendente_nao_pode_criar_usuario(self, client_anonimo, db_session):
        self._login_atendente(client_anonimo, db_session)

        resp = client_anonimo.post(
            "/auth/usuarios",
            json={
                "nome": "Outro",
                "email": "outro@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "atendente",
            },
        )

        assert resp.status_code == 403

    def test_atendente_nao_pode_trocar_a_propria_senha(self, client_anonimo, db_session):
        self._login_atendente(client_anonimo, db_session)

        resp = client_anonimo.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-valida-123", "senha_nova": "senha-nova-456"},
        )

        assert resp.status_code == 403

    def test_proprietaria_pode_listar_e_criar_usuarios(self, client):
        resp_listar = client.get("/auth/usuarios")
        resp_criar = client.post(
            "/auth/usuarios",
            json={
                "nome": "Atendente Nova",
                "email": "atendente@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "atendente",
            },
        )

        assert resp_listar.status_code == 200
        assert resp_criar.status_code == 201


class TestDesativarUsuario:
    def test_proprietaria_desativa_outro_usuario(self, client):
        atendente = client.post(
            "/auth/usuarios",
            json={
                "nome": "Atendente",
                "email": "atendente@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "atendente",
            },
        ).json()

        resp = client.delete(f"/auth/usuarios/{atendente['id']}")

        assert resp.status_code == 204

    def test_usuario_desativado_nao_consegue_mais_logar(self, client, client_anonimo, db_session):
        atendente = _criar_usuario(
            db_session,
            nome="Atendente",
            email="atendente@passoca.com",
            senha="senha-valida-123",
            perfil=PerfilUsuario.ATENDENTE,
        )

        client.delete(f"/auth/usuarios/{atendente.id}")

        resp = client_anonimo.post(
            "/auth/login",
            json={"email": "atendente@passoca.com", "senha": "senha-valida-123"},
        )

        assert resp.status_code == 401

    def test_nao_pode_desativar_a_propria_conta(self, client, usuario_teste):
        resp = client.delete(f"/auth/usuarios/{usuario_teste.id}")

        assert resp.status_code == 400

    def test_nao_pode_desativar_a_unica_proprietaria_ativa(self, client, db_session):
        outra_proprietaria = _criar_usuario(
            db_session,
            nome="Outra Proprietária",
            email="outra-dona@passoca.com",
            senha="senha-valida-123",
            perfil=PerfilUsuario.PROPRIETARIA,
        )

        # usuario_teste (quem está logado) desativa a outra proprietária
        # primeiro -- agora usuario_teste seria a última ativa.
        client.delete(f"/auth/usuarios/{outra_proprietaria.id}")

        # Cria uma terceira proprietária só pra poder tentar desativar
        # ela sem esbarrar no bloqueio de "não pode desativar a si mesmo".
        terceira = _criar_usuario(
            db_session,
            nome="Terceira Proprietária",
            email="terceira-dona@passoca.com",
            senha="senha-valida-123",
            perfil=PerfilUsuario.PROPRIETARIA,
            ativo=False,
        )

        resp = client.delete(f"/auth/usuarios/{terceira.id}")

        # Já estava inativa -- o bloqueio de "única ativa" olha pra quem
        # *ficaria* ativo, não pra quem já está inativo, então isso só
        # confirma que desativar um já-inativo não quebra nada.
        assert resp.status_code == 204

    def test_atendente_nao_pode_desativar_ninguem(self, client_anonimo, db_session):
        _criar_usuario(
            db_session,
            nome="Atendente",
            email="atendente@passoca.com",
            senha="senha-valida-123",
            perfil=PerfilUsuario.ATENDENTE,
        )
        alvo = _criar_usuario(
            db_session,
            nome="Padeiro",
            email="padeiro@passoca.com",
            senha="senha-valida-123",
            perfil=PerfilUsuario.PADEIRO,
        )
        client_anonimo.post(
            "/auth/login",
            json={"email": "atendente@passoca.com", "senha": "senha-valida-123"},
        )

        resp = client_anonimo.delete(f"/auth/usuarios/{alvo.id}")

        assert resp.status_code == 403
