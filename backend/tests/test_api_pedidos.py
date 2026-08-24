"""Testes de integração da API de Pedido — RF03/RF04 e RN01."""
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
