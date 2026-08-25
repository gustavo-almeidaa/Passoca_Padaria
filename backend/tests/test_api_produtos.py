"""Testes de integração da API de Produto — RF02."""


def test_criar_produto_sucesso(client):
    payload = {
        "nome": "Bolo de Chocolate",
        "categoria": "bolo",
        "unidade": "unidade",
        "preco": "45.90",
        "personalizavel": True,
    }

    resp = client.post("/produtos", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Bolo de Chocolate"
    assert data["personalizavel"] is True
    assert data["ativo"] is True  # default


def test_criar_produto_preco_negativo_e_rejeitado(client):
    payload = {
        "nome": "Pão Francês",
        "categoria": "pao",
        "unidade": "kg",
        "preco": "-1",
    }

    resp = client.post("/produtos", json=payload)

    assert resp.status_code == 422


def test_criar_produto_categoria_invalida_e_rejeitada(client):
    payload = {
        "nome": "X",
        "categoria": "invalida",
        "unidade": "kg",
        "preco": "1",
    }

    resp = client.post("/produtos", json=payload)

    assert resp.status_code == 422


def test_listar_produtos_filtra_por_ativo(client):
    client.post(
        "/produtos",
        json={"nome": "A", "categoria": "pao", "unidade": "kg", "preco": "1", "ativo": True},
    )
    client.post(
        "/produtos",
        json={"nome": "B", "categoria": "pao", "unidade": "kg", "preco": "1", "ativo": False},
    )

    resp = client.get("/produtos", params={"ativo": True})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["nome"] == "A"


def test_obter_produto_inexistente_retorna_404(client):
    resp = client.get("/produtos/9999")

    assert resp.status_code == 404
    assert "não encontrado" in resp.json()["detail"].lower()


def test_criar_produto_preco_acima_do_teto_e_rejeitado(client):
    payload = {
        "nome": "Bolo Gigante",
        "categoria": "bolo",
        "unidade": "unidade",
        "preco": "1000.00",
    }

    resp = client.post("/produtos", json=payload)

    assert resp.status_code == 422


def test_criar_produto_preco_no_teto_e_aceito(client):
    payload = {
        "nome": "Bolo Caro",
        "categoria": "bolo",
        "unidade": "unidade",
        "preco": "999.99",
    }

    resp = client.post("/produtos", json=payload)

    assert resp.status_code == 201


class TestEditarProduto:
    def _criar(self, client, **overrides):
        payload = {
            "nome": "Bolo de Chocolate",
            "categoria": "bolo",
            "unidade": "unidade",
            "preco": "45.90",
            "personalizavel": False,
            "ativo": True,
        }
        payload.update(overrides)
        return client.post("/produtos", json=payload).json()

    def test_editar_produto_sucesso(self, client):
        produto = self._criar(client)

        resp = client.put(
            f"/produtos/{produto['id']}",
            json={
                "nome": "Bolo de Chocolate Grande",
                "categoria": "bolo",
                "unidade": "unidade",
                "preco": "59.90",
                "personalizavel": True,
                "ativo": True,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["nome"] == "Bolo de Chocolate Grande"
        assert data["preco"] == "59.90"
        assert data["personalizavel"] is True

    def test_editar_produto_nao_afeta_pedido_ja_feito(self, client, db_session):
        from datetime import date, time

        from app.models.cliente import Cliente
        from app.models.item_pedido import ItemPedido
        from app.models.pedido import Pedido

        produto = self._criar(client, preco="10.00")

        cliente = Cliente(nome="Maria", telefone="43999990000")
        db_session.add(cliente)
        db_session.commit()

        pedido = Pedido(
            cliente_id=cliente.id, data_entrega=date(2026, 12, 25), hora_entrega=time(14, 0)
        )
        db_session.add(pedido)
        db_session.commit()

        item = ItemPedido(
            pedido_id=pedido.id, produto_id=produto["id"], quantidade=1, preco_unitario="10.00"
        )
        db_session.add(item)
        db_session.commit()

        client.put(
            f"/produtos/{produto['id']}",
            json={
                "nome": "Bolo de Chocolate",
                "categoria": "bolo",
                "unidade": "unidade",
                "preco": "99.90",
                "personalizavel": False,
                "ativo": True,
            },
        )

        db_session.refresh(item)
        assert str(item.preco_unitario) == "10.00"

    def test_editar_produto_inexistente_retorna_404(self, client):
        resp = client.put(
            "/produtos/9999",
            json={
                "nome": "X",
                "categoria": "bolo",
                "unidade": "unidade",
                "preco": "10.00",
            },
        )

        assert resp.status_code == 404

    def test_editar_produto_preco_acima_do_teto_e_rejeitado(self, client):
        produto = self._criar(client)

        resp = client.put(
            f"/produtos/{produto['id']}",
            json={
                "nome": "Bolo de Chocolate",
                "categoria": "bolo",
                "unidade": "unidade",
                "preco": "1000.00",
            },
        )

        assert resp.status_code == 422
