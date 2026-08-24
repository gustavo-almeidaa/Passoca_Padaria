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
