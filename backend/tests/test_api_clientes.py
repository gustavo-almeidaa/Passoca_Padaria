"""Testes de integração da API de Cliente — RF01."""


def test_criar_cliente_sucesso(client):
    resp = client.post("/clientes", json={"nome": "Maria", "telefone": "11999998888"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Maria"
    assert data["telefone"] == "11999998888"
    assert "id" in data
    assert "criado_em" in data


def test_criar_cliente_nome_vazio_e_rejeitado(client):
    resp = client.post("/clientes", json={"nome": "   ", "telefone": "11999998888"})

    assert resp.status_code == 422


def test_criar_cliente_telefone_invalido_e_rejeitado(client):
    resp = client.post("/clientes", json={"nome": "Maria", "telefone": "123"})

    assert resp.status_code == 422


def test_listar_clientes_ordenado_por_nome(client):
    client.post("/clientes", json={"nome": "Bia", "telefone": "11999998888"})
    client.post("/clientes", json={"nome": "Ana", "telefone": "11988887777"})

    resp = client.get("/clientes")

    assert resp.status_code == 200
    nomes = [c["nome"] for c in resp.json()]
    assert nomes == ["Ana", "Bia"]


def test_obter_cliente_existente(client):
    criado = client.post(
        "/clientes", json={"nome": "Carla", "telefone": "11999998888"}
    ).json()

    resp = client.get(f"/clientes/{criado['id']}")

    assert resp.status_code == 200
    assert resp.json()["nome"] == "Carla"


def test_obter_cliente_inexistente_retorna_404_com_mensagem_clara(client):
    resp = client.get("/clientes/9999")

    assert resp.status_code == 404
    assert "não encontrado" in resp.json()["detail"].lower()
