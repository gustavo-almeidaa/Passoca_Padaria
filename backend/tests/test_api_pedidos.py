"""Testes de integração da API de Pedido — RF03-RF07 e RN01-RN04."""
from datetime import datetime, timedelta


def _criar_cliente(client, nome="Maria Silva"):
    resp = client.post("/clientes", json={"nome": nome, "telefone": "43999990000"})
    return resp.json()["id"]


def _criar_produto(
    client,
    nome="Bolo de Chocolate",
    preco="45.90",
    personalizavel=False,
    ativo=True,
):
    resp = client.post(
        "/produtos",
        json={
            "nome": nome,
            "categoria": "bolo",
            "unidade": "unidade",
            "preco": preco,
            "personalizavel": personalizavel,
            "ativo": ativo,
        },
    )
    return resp.json()["id"]


def _entrega(delta: timedelta) -> tuple[str, str]:
    """Data/hora de entrega relativa a `agora`, formatada pra JSON."""
    momento = datetime.now() + delta
    return momento.date().isoformat(), momento.time().replace(microsecond=0).isoformat()


def _payload(cliente_id, produto_id, delta=timedelta(days=3), quantidade=2):
    data, hora = _entrega(delta)
    return {
        "cliente_id": cliente_id,
        "data_entrega": data,
        "hora_entrega": hora,
        "itens": [{"produto_id": produto_id, "quantidade": quantidade}],
    }


def test_criar_pedido_sucesso(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)

    resp = client.post("/pedidos", json=_payload(cliente_id, produto_id))

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["cliente_id"] == cliente_id
    assert corpo["status"] == "recebido"
    assert corpo["sinal_confirmado"] is False
    assert len(corpo["itens"]) == 1
    assert corpo["itens"][0]["produto_id"] == produto_id
    assert corpo["itens"][0]["quantidade"] == 2
    assert corpo["itens"][0]["preco_unitario"] == "45.90"


def test_criar_pedido_com_menos_de_24h_e_rejeitado(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)

    resp = client.post(
        "/pedidos", json=_payload(cliente_id, produto_id, delta=timedelta(hours=2))
    )

    assert resp.status_code == 422
    assert "24h" in resp.json()["detail"]


def test_criar_pedido_cliente_inexistente_retorna_404(client):
    produto_id = _criar_produto(client)

    resp = client.post("/pedidos", json=_payload(9999, produto_id))

    assert resp.status_code == 404
    assert "não encontrado" in resp.json()["detail"].lower()


def test_criar_pedido_produto_inexistente_e_rejeitado(client):
    cliente_id = _criar_cliente(client)

    resp = client.post("/pedidos", json=_payload(cliente_id, 9999))

    assert resp.status_code == 422


def test_criar_pedido_produto_inativo_e_rejeitado(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client, ativo=False)

    resp = client.post("/pedidos", json=_payload(cliente_id, produto_id))

    assert resp.status_code == 422
    assert "disponível" in resp.json()["detail"].lower()


def test_criar_pedido_quantidade_invalida_e_rejeitada(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)

    resp = client.post(
        "/pedidos", json=_payload(cliente_id, produto_id, quantidade=0)
    )

    assert resp.status_code == 422


def test_criar_pedido_quantidade_acima_do_teto_e_rejeitada(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)

    resp = client.post(
        "/pedidos", json=_payload(cliente_id, produto_id, quantidade=1000)
    )

    assert resp.status_code == 422


def test_criar_pedido_quantidade_no_teto_e_aceita(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)

    resp = client.post(
        "/pedidos", json=_payload(cliente_id, produto_id, quantidade=999)
    )

    assert resp.status_code == 201


def test_criar_pedido_com_mais_de_90_dias_de_antecedencia_e_rejeitado(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)

    resp = client.post(
        "/pedidos", json=_payload(cliente_id, produto_id, delta=timedelta(days=91))
    )

    assert resp.status_code == 422
    assert "90 dias" in resp.json()["detail"]


def test_criar_pedido_sem_itens_e_rejeitado(client):
    cliente_id = _criar_cliente(client)
    data, hora = _entrega(timedelta(days=3))

    resp = client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "data_entrega": data,
            "hora_entrega": hora,
            "itens": [],
        },
    )

    assert resp.status_code == 422


def test_obter_pedido_inexistente_retorna_404(client):
    resp = client.get("/pedidos/9999")

    assert resp.status_code == 404
    assert "não encontrado" in resp.json()["detail"].lower()


def test_obter_pedido_existente_traz_itens(client):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client)
    criado = client.post("/pedidos", json=_payload(cliente_id, produto_id)).json()

    resp = client.get(f"/pedidos/{criado['id']}")

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["id"] == criado["id"]
    assert len(corpo["itens"]) == 1


def _criar_pedido(client, *, personalizavel=False, delta=timedelta(days=3)):
    cliente_id = _criar_cliente(client)
    produto_id = _criar_produto(client, personalizavel=personalizavel)
    resp = client.post("/pedidos", json=_payload(cliente_id, produto_id, delta=delta))
    return resp.json()


class TestConfirmarSinalAPI:
    def test_confirma_sinal_com_sucesso(self, client):
        pedido = _criar_pedido(client, personalizavel=True)

        resp = client.post(f"/pedidos/{pedido['id']}/confirmar-sinal")

        assert resp.status_code == 200
        assert resp.json()["sinal_confirmado"] is True

    def test_pedido_inexistente_retorna_404(self, client):
        resp = client.post("/pedidos/9999/confirmar-sinal")

        assert resp.status_code == 404


class TestAvancarPedidoAPI:
    """RF: avançar status (UC04) — RN02 e RN04 aplicadas via API."""

    def test_avanca_pedido_sem_item_personalizavel(self, client):
        pedido = _criar_pedido(client, personalizavel=False)

        resp = client.post(f"/pedidos/{pedido['id']}/avancar")

        assert resp.status_code == 200
        assert resp.json()["status"] == "em_producao"

    def test_avanco_com_item_personalizavel_sem_sinal_e_rejeitado(self, client):
        pedido = _criar_pedido(client, personalizavel=True)

        resp = client.post(f"/pedidos/{pedido['id']}/avancar")

        assert resp.status_code == 422
        assert "sinal" in resp.json()["detail"].lower()

    def test_avanco_com_item_personalizavel_e_sinal_confirmado(self, client):
        pedido = _criar_pedido(client, personalizavel=True)
        client.post(f"/pedidos/{pedido['id']}/confirmar-sinal")

        resp = client.post(f"/pedidos/{pedido['id']}/avancar")

        assert resp.status_code == 200
        assert resp.json()["status"] == "em_producao"

    def test_avanco_ate_entregue_e_depois_rejeitado(self, client):
        pedido = _criar_pedido(client, personalizavel=False)
        pedido_id = pedido["id"]

        for status_esperado in ("em_producao", "pronto", "entregue"):
            resp = client.post(f"/pedidos/{pedido_id}/avancar")
            assert resp.status_code == 200
            assert resp.json()["status"] == status_esperado

        resp = client.post(f"/pedidos/{pedido_id}/avancar")
        assert resp.status_code == 422

    def test_pedido_inexistente_retorna_404(self, client):
        resp = client.post("/pedidos/9999/avancar")

        assert resp.status_code == 404


class TestCancelarPedidoAPI:
    """RF06 — RN03 (janela) e RN04 (só recebido/em_producao) via API.

    A janela de 12h em si (limite exato) já tem cobertura dedicada no
    service (test_services_pedidos.py, com `agora` injetável) — aqui só o
    caminho feliz e a rejeição por status, que não dependem de manipular o
    relógio.
    """

    def test_cancela_pedido_recem_criado(self, client):
        pedido = _criar_pedido(client)

        resp = client.post(f"/pedidos/{pedido['id']}/cancelar")

        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelado"

    def test_cancelar_pedido_ja_entregue_e_rejeitado(self, client):
        pedido = _criar_pedido(client, personalizavel=False)
        pedido_id = pedido["id"]
        for _ in range(3):
            client.post(f"/pedidos/{pedido_id}/avancar")

        resp = client.post(f"/pedidos/{pedido_id}/cancelar")

        assert resp.status_code == 422

    def test_cancelar_pedido_ja_cancelado_e_rejeitado(self, client):
        pedido = _criar_pedido(client)
        client.post(f"/pedidos/{pedido['id']}/cancelar")

        resp = client.post(f"/pedidos/{pedido['id']}/cancelar")

        assert resp.status_code == 422

    def test_pedido_inexistente_retorna_404(self, client):
        resp = client.post("/pedidos/9999/cancelar")

        assert resp.status_code == 404


class TestListarPedidosAPI:
    def test_lista_pedidos_do_dia_da_entrega(self, client):
        pedido = _criar_pedido(client, delta=timedelta(days=3))
        data_entrega = pedido["data_entrega"]

        resp = client.get(f"/pedidos?data_inicio={data_entrega}")

        assert resp.status_code == 200
        ids = {p["id"] for p in resp.json()}
        assert pedido["id"] in ids

    def test_lista_vazia_fora_do_periodo(self, client):
        pedido = _criar_pedido(client, delta=timedelta(days=3))
        outra_data, _ = _entrega(timedelta(days=30))

        resp = client.get(f"/pedidos?data_inicio={outra_data}")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_data_fim_anterior_a_data_inicio_e_rejeitada(self, client):
        resp = client.get("/pedidos?data_inicio=2026-02-10&data_fim=2026-02-01")

        assert resp.status_code == 422

    def test_sem_data_inicio_e_rejeitado(self, client):
        resp = client.get("/pedidos")

        assert resp.status_code == 422
