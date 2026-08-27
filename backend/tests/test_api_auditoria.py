"""Testes de integração da trilha de auditoria — Incremento 18 (A-01).

Cobre: cada operação sensível gera exatamente um evento, com autoria e
estado antes/depois corretos; operações de leitura não geram nada; e o
endpoint `GET /auditoria` é exclusivo da proprietária.
"""
from datetime import datetime, timedelta

from app.core.security import hash_senha
from app.models.evento_auditoria import EventoAuditoria
from app.models.usuario import PerfilUsuario, Usuario


def _entrega(dias=3):
    m = datetime.now() + timedelta(days=dias)
    return m.date().isoformat(), m.time().replace(microsecond=0).isoformat()


def _cliente(client):
    return client.post(
        "/clientes", json={"nome": "Maria", "telefone": "43999990000"}
    ).json()["id"]


def _produto(client, preco="45.90", personalizavel=False):
    return client.post(
        "/produtos",
        json={
            "nome": "Bolo",
            "categoria": "bolo",
            "unidade": "unidade",
            "preco": preco,
            "personalizavel": personalizavel,
        },
    ).json()["id"]


def _pedido(client, personalizavel=False):
    cid = _cliente(client)
    pid = _produto(client, personalizavel=personalizavel)
    data, hora = _entrega()
    return client.post(
        "/pedidos",
        json={
            "cliente_id": cid,
            "data_entrega": data,
            "hora_entrega": hora,
            "itens": [{"produto_id": pid, "quantidade": 2}],
        },
    ).json()


def _eventos(db_session, **filtros):
    q = db_session.query(EventoAuditoria)
    for campo, valor in filtros.items():
        q = q.filter(getattr(EventoAuditoria, campo) == valor)
    return q.order_by(EventoAuditoria.id).all()


class TestGravacaoPedido:
    def test_criar_pedido_gera_evento(self, client, db_session, usuario_teste):
        pedido = _pedido(client)

        eventos = _eventos(db_session, entidade="pedido", acao="criar")
        assert len(eventos) == 1
        ev = eventos[0]
        assert ev.entidade_id == pedido["id"]
        assert ev.usuario_id == usuario_teste.id
        assert ev.usuario_email == usuario_teste.email
        assert ev.estado_anterior is None
        assert ev.estado_posterior["status"] == "recebido"
        assert len(ev.estado_posterior["itens"]) == 1

    def test_avancar_pedido_registra_antes_e_depois(self, client, db_session):
        pedido = _pedido(client)
        client.post(f"/pedidos/{pedido['id']}/avancar")

        ev = _eventos(db_session, entidade="pedido", acao="avancar_status")[0]
        assert ev.estado_anterior["status"] == "recebido"
        assert ev.estado_posterior["status"] == "em_producao"

    def test_confirmar_sinal_gera_evento(self, client, db_session):
        pedido = _pedido(client, personalizavel=True)
        client.post(f"/pedidos/{pedido['id']}/confirmar-sinal")

        ev = _eventos(db_session, entidade="pedido", acao="confirmar_sinal")[0]
        assert ev.estado_anterior["sinal_confirmado"] is False
        assert ev.estado_posterior["sinal_confirmado"] is True

    def test_cancelar_pedido_gera_evento(self, client, db_session):
        pedido = _pedido(client)
        client.post(f"/pedidos/{pedido['id']}/cancelar")

        ev = _eventos(db_session, entidade="pedido", acao="cancelar")[0]
        assert ev.estado_posterior["status"] == "cancelado"

    def test_pedido_invalido_nao_gera_evento(self, client, db_session):
        # Antecedência < 24h é rejeitada — nenhum evento deve sobrar.
        cid = _cliente(client)
        pid = _produto(client)
        m = datetime.now() + timedelta(hours=2)
        resp = client.post(
            "/pedidos",
            json={
                "cliente_id": cid,
                "data_entrega": m.date().isoformat(),
                "hora_entrega": m.time().replace(microsecond=0).isoformat(),
                "itens": [{"produto_id": pid, "quantidade": 1}],
            },
        )
        assert resp.status_code == 422
        assert _eventos(db_session, entidade="pedido") == []


class TestGravacaoProduto:
    def test_criar_produto_gera_evento(self, client, db_session):
        pid = _produto(client, preco="10.00")

        ev = _eventos(db_session, entidade="produto", acao="criar")[0]
        assert ev.entidade_id == pid
        assert ev.estado_posterior["preco"] == "10.00"

    def test_editar_produto_registra_preco_antigo_e_novo(self, client, db_session):
        pid = _produto(client, preco="10.00")
        client.put(
            f"/produtos/{pid}",
            json={
                "nome": "Bolo",
                "categoria": "bolo",
                "unidade": "unidade",
                "preco": "25.00",
                "personalizavel": False,
            },
        )

        ev = _eventos(db_session, entidade="produto", acao="editar")[0]
        assert ev.estado_anterior["preco"] == "10.00"
        assert ev.estado_posterior["preco"] == "25.00"


class TestGravacaoUsuario:
    def test_criar_usuario_gera_evento(self, client, db_session):
        novo = client.post(
            "/auth/usuarios",
            json={
                "nome": "Padeiro",
                "email": "padeiro@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "padeiro",
            },
        ).json()

        ev = _eventos(db_session, entidade="usuario", acao="criar")[0]
        assert ev.entidade_id == novo["id"]
        assert ev.estado_posterior["perfil"] == "padeiro"
        assert "senha" not in ev.estado_posterior

    def test_desativar_usuario_gera_evento(self, client, db_session):
        alvo = client.post(
            "/auth/usuarios",
            json={
                "nome": "Atendente",
                "email": "atendente@passoca.com",
                "senha": "senha-valida-123",
                "perfil": "atendente",
            },
        ).json()
        client.delete(f"/auth/usuarios/{alvo['id']}")

        ev = _eventos(db_session, entidade="usuario", acao="desativar")[0]
        assert ev.estado_anterior == {"ativo": True}
        assert ev.estado_posterior == {"ativo": False}

    def test_trocar_senha_nao_grava_o_valor(self, client, db_session, usuario_teste):
        client.post(
            "/auth/trocar-senha",
            json={"senha_atual": "senha-de-teste-123", "senha_nova": "senha-nova-999"},
        )

        ev = _eventos(db_session, entidade="usuario", acao="trocar_senha")[0]
        assert ev.estado_posterior == {"senha": "alterada"}


class TestLeituraNaoGeraEvento:
    def test_listar_e_consultar_nao_geram_eventos(self, client, db_session):
        pedido = _pedido(client)
        client.get("/pedidos", params={"data_inicio": _entrega()[0]})
        client.get(f"/pedidos/{pedido['id']}")
        client.get("/produtos")

        # Só o evento de criação do pedido (e o de criação do produto dele).
        acoes = {e.acao for e in _eventos(db_session)}
        assert acoes == {"criar"}

    def test_criar_cliente_nao_gera_evento(self, client, db_session):
        _cliente(client)
        assert _eventos(db_session, entidade="cliente") == []


class TestSnapshotSobreviveAMudanca:
    def test_evento_mantem_email_apos_usuario_desativado(
        self, client, db_session, usuario_teste
    ):
        outra = Usuario(
            nome="Outra Dona",
            email="outra@passoca.com",
            senha_hash=hash_senha("senha-valida-123"),
            perfil=PerfilUsuario.PROPRIETARIA,
        )
        db_session.add(outra)
        db_session.commit()

        _produto(client)  # usuario_teste gera um evento
        client.delete(f"/auth/usuarios/{outra.id}")

        ev = _eventos(db_session, entidade="produto")[0]
        assert ev.usuario_email == usuario_teste.email


class TestEndpointAuditoria:
    def test_proprietaria_lista_eventos(self, client, db_session):
        _produto(client)

        resp = client.get("/auditoria")

        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert resp.json()[0]["entidade"] == "produto"

    def test_filtra_por_entidade(self, client):
        _pedido(client)  # gera eventos de produto E de pedido

        resp = client.get("/auditoria", params={"entidade": "pedido"})

        assert resp.status_code == 200
        assert all(e["entidade"] == "pedido" for e in resp.json())
        assert len(resp.json()) >= 1

    def test_filtra_por_entidade_id(self, client):
        pid = _produto(client)
        _produto(client)

        resp = client.get("/auditoria", params={"entidade_id": pid})

        assert resp.status_code == 200
        assert all(e["entidade_id"] == pid for e in resp.json())

    def test_limite_respeitado(self, client):
        for _ in range(3):
            _produto(client)

        resp = client.get("/auditoria", params={"limite": 2})

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_ordem_mais_recente_primeiro(self, client):
        _produto(client, preco="1.00")
        _produto(client, preco="2.00")

        eventos = client.get("/auditoria", params={"entidade": "produto"}).json()

        assert eventos[0]["id"] > eventos[1]["id"]

    def test_atendente_recebe_403(self, client_anonimo, db_session):
        atendente = Usuario(
            nome="Atendente",
            email="atendente@passoca.com",
            senha_hash=hash_senha("senha-valida-123"),
            perfil=PerfilUsuario.ATENDENTE,
        )
        db_session.add(atendente)
        db_session.commit()
        client_anonimo.post(
            "/auth/login",
            json={"email": "atendente@passoca.com", "senha": "senha-valida-123"},
        )

        resp = client_anonimo.get("/auditoria")

        assert resp.status_code == 403

    def test_sem_sessao_recebe_401(self, client_anonimo):
        resp = client_anonimo.get("/auditoria")

        assert resp.status_code == 401
