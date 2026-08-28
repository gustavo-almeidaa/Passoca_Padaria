"""Matriz de permissão por perfil — Incremento 19 (auditoria A-03).

Para cada operação restrita: o padeiro recebe 403, e proprietária/atendente
conseguem. Operações de leitura ficam abertas a qualquer perfil.

Os testes usam o fluxo de login real (client_anonimo), não o override de
autenticação — é a autorização que está sendo testada.
"""
from datetime import datetime, timedelta

import pytest

from app.core.security import hash_senha
from app.models.usuario import PerfilUsuario, Usuario

PERFIL = {
    "proprietaria": PerfilUsuario.PROPRIETARIA,
    "atendente": PerfilUsuario.ATENDENTE,
    "padeiro": PerfilUsuario.PADEIRO,
}


def _logar(client_anonimo, db_session, perfil_str):
    usuario = Usuario(
        nome=f"User {perfil_str}",
        email=f"{perfil_str}@passoca.com",
        senha_hash=hash_senha("senha-valida-123"),
        perfil=PERFIL[perfil_str],
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    client_anonimo.post(
        "/auth/login",
        json={"email": f"{perfil_str}@passoca.com", "senha": "senha-valida-123"},
    )
    return usuario


def _cliente(client_anonimo):
    return client_anonimo.post(
        "/clientes", json={"nome": "Maria", "telefone": "43999990000"}
    ).json()["id"]


def _produto(client_anonimo, personalizavel=False):
    return client_anonimo.post(
        "/produtos",
        json={
            "nome": "Bolo",
            "categoria": "bolo",
            "unidade": "unidade",
            "preco": "20.00",
            "personalizavel": personalizavel,
        },
    ).json()["id"]


def _pedido(client_anonimo, personalizavel=False):
    cid = _cliente(client_anonimo)
    pid = _produto(client_anonimo, personalizavel=personalizavel)
    m = datetime.now() + timedelta(days=3)
    return client_anonimo.post(
        "/pedidos",
        json={
            "cliente_id": cid,
            "data_entrega": m.date().isoformat(),
            "hora_entrega": m.time().replace(microsecond=0).isoformat(),
            "itens": [{"produto_id": pid, "quantidade": 1}],
        },
    ).json()


# --- Operações de balcão: proprietária e atendente OK, padeiro 403 --------

class TestPadeiroBloqueado:
    def test_padeiro_nao_cadastra_cliente(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "padeiro")
        resp = client_anonimo.post(
            "/clientes", json={"nome": "X", "telefone": "43900000000"}
        )
        assert resp.status_code == 403
        assert "padeiro" in resp.json()["detail"].lower()

    def test_padeiro_nao_cadastra_produto(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "padeiro")
        resp = client_anonimo.post(
            "/produtos",
            json={"nome": "X", "categoria": "pao", "unidade": "kg", "preco": "1"},
        )
        assert resp.status_code == 403

    def test_padeiro_nao_edita_produto(self, client_anonimo, db_session):
        # Cria o produto como proprietária primeiro.
        _logar(client_anonimo, db_session, "proprietaria")
        pid = _produto(client_anonimo)
        client_anonimo.post("/auth/logout")

        _logar(client_anonimo, db_session, "padeiro")
        resp = client_anonimo.put(
            f"/produtos/{pid}",
            json={
                "nome": "Bolo", "categoria": "bolo", "unidade": "unidade",
                "preco": "999.00", "personalizavel": False,
            },
        )
        assert resp.status_code == 403

    def test_padeiro_nao_registra_pedido(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "proprietaria")
        cid = _cliente(client_anonimo)
        pid = _produto(client_anonimo)
        client_anonimo.post("/auth/logout")

        _logar(client_anonimo, db_session, "padeiro")
        m = datetime.now() + timedelta(days=3)
        resp = client_anonimo.post(
            "/pedidos",
            json={
                "cliente_id": cid,
                "data_entrega": m.date().isoformat(),
                "hora_entrega": m.time().replace(microsecond=0).isoformat(),
                "itens": [{"produto_id": pid, "quantidade": 1}],
            },
        )
        assert resp.status_code == 403

    def test_padeiro_nao_confirma_sinal(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "proprietaria")
        pedido = _pedido(client_anonimo, personalizavel=True)
        client_anonimo.post("/auth/logout")

        _logar(client_anonimo, db_session, "padeiro")
        resp = client_anonimo.post(f"/pedidos/{pedido['id']}/confirmar-sinal")
        assert resp.status_code == 403

    def test_padeiro_nao_cancela_pedido(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "proprietaria")
        pedido = _pedido(client_anonimo)
        client_anonimo.post("/auth/logout")

        _logar(client_anonimo, db_session, "padeiro")
        resp = client_anonimo.post(f"/pedidos/{pedido['id']}/cancelar")
        assert resp.status_code == 403

    def test_padeiro_nao_edita_pedido(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "proprietaria")
        pedido = _pedido(client_anonimo)
        produto_id = pedido["itens"][0]["produto_id"]
        client_anonimo.post("/auth/logout")

        _logar(client_anonimo, db_session, "padeiro")
        m = datetime.now() + timedelta(days=5)
        resp = client_anonimo.put(
            f"/pedidos/{pedido['id']}",
            json={
                "data_entrega": m.date().isoformat(),
                "hora_entrega": m.time().replace(microsecond=0).isoformat(),
                "itens": [{"produto_id": produto_id, "quantidade": 3}],
            },
        )
        assert resp.status_code == 403


# --- O que o padeiro PODE: ler tudo e avançar status ---------------------

class TestPadeiroPermitido:
    def test_padeiro_lista_pedidos_produtos_clientes(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "padeiro")
        assert client_anonimo.get("/clientes").status_code == 200
        assert client_anonimo.get("/produtos").status_code == 200
        assert client_anonimo.get(
            "/pedidos", params={"data_inicio": "2026-01-01"}
        ).status_code == 200

    def test_padeiro_avanca_status_de_producao(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "proprietaria")
        pedido = _pedido(client_anonimo)
        client_anonimo.post("/auth/logout")

        _logar(client_anonimo, db_session, "padeiro")
        resp = client_anonimo.post(f"/pedidos/{pedido['id']}/avancar")
        assert resp.status_code == 200
        assert resp.json()["status"] == "em_producao"


# --- Atendente: faz tudo de balcão (inclusive editar produto e cancelar) -

class TestAtendentePermitido:
    @pytest.mark.parametrize("perfil", ["proprietaria", "atendente"])
    def test_cadastra_cliente_produto_e_pedido(self, client_anonimo, db_session, perfil):
        _logar(client_anonimo, db_session, perfil)
        pedido = _pedido(client_anonimo)
        assert pedido.get("id") is not None

    def test_atendente_edita_produto(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "atendente")
        pid = _produto(client_anonimo)
        resp = client_anonimo.put(
            f"/produtos/{pid}",
            json={
                "nome": "Bolo", "categoria": "bolo", "unidade": "unidade",
                "preco": "30.00", "personalizavel": False,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["preco"] == "30.00"

    def test_atendente_cancela_pedido(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "atendente")
        pedido = _pedido(client_anonimo)
        resp = client_anonimo.post(f"/pedidos/{pedido['id']}/cancelar")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelado"


class TestGatesProprietariaInalterados:
    """O Incremento 15/18 já restringia Usuários e Auditoria — segue igual."""

    def test_atendente_nao_acessa_usuarios_nem_auditoria(self, client_anonimo, db_session):
        _logar(client_anonimo, db_session, "atendente")
        assert client_anonimo.get("/auth/usuarios").status_code == 403
        assert client_anonimo.get("/auditoria").status_code == 403
