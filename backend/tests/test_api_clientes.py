"""Testes de integração da API de Cliente — RF01 e histórico (Incremento 24)."""
from datetime import datetime, timedelta


def test_criar_cliente_sucesso(client):
    resp = client.post("/clientes", json={"nome": "Maria", "telefone": "11999998888"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Maria"
    assert data["telefone"] == "11999998888"
    assert data["endereco"] is None
    assert "id" in data
    assert "criado_em" in data


def test_criar_cliente_com_endereco(client):
    resp = client.post(
        "/clientes",
        json={
            "nome": "Maria",
            "telefone": "11999998888",
            "endereco": "Rua das Flores, 123, Centro",
        },
    )

    assert resp.status_code == 201
    assert resp.json()["endereco"] == "Rua das Flores, 123, Centro"


def test_criar_cliente_endereco_em_branco_vira_none(client):
    resp = client.post(
        "/clientes",
        json={"nome": "Maria", "telefone": "11999998888", "endereco": "   "},
    )

    assert resp.status_code == 201
    assert resp.json()["endereco"] is None


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


def _cliente(client, nome="Maria"):
    return client.post("/clientes", json={"nome": nome, "telefone": "11999998888"}).json()["id"]


def _produto(client):
    return client.post(
        "/produtos",
        json={"nome": "Bolo", "categoria": "bolo", "unidade": "unidade", "preco": "20.00"},
    ).json()["id"]


def _pedido(client, cliente_id, produto_id, dias):
    m = datetime.now() + timedelta(days=dias)
    return client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "data_entrega": m.date().isoformat(),
            "hora_entrega": m.time().replace(microsecond=0).isoformat(),
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    ).json()


class TestHistoricoDePedidos:
    def test_lista_os_pedidos_do_cliente_do_mais_recente_pro_mais_antigo(self, client):
        cid = _cliente(client)
        pid = _produto(client)
        _pedido(client, cid, pid, dias=2)
        _pedido(client, cid, pid, dias=10)
        _pedido(client, cid, pid, dias=5)

        resp = client.get(f"/clientes/{cid}/pedidos")

        assert resp.status_code == 200
        datas = [p["data_entrega"] for p in resp.json()]
        assert datas == sorted(datas, reverse=True)
        assert len(resp.json()) == 3

    def test_nao_vaza_pedido_de_outro_cliente(self, client):
        pid = _produto(client)
        alvo = _cliente(client, "Alvo")
        outro = _cliente(client, "Outro")
        _pedido(client, alvo, pid, dias=3)
        _pedido(client, outro, pid, dias=3)

        resp = client.get(f"/clientes/{alvo}/pedidos")

        assert len(resp.json()) == 1
        assert resp.json()[0]["cliente_id"] == alvo

    def test_cliente_sem_pedidos_retorna_lista_vazia(self, client):
        cid = _cliente(client)

        resp = client.get(f"/clientes/{cid}/pedidos")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_cliente_inexistente_retorna_404(self, client):
        resp = client.get("/clientes/9999/pedidos")

        assert resp.status_code == 404

    def test_qualquer_perfil_autenticado_le_o_historico(self, client_anonimo, db_session):
        from app.core.security import hash_senha
        from app.models.usuario import PerfilUsuario, Usuario

        padeiro = Usuario(
            nome="Padeiro", email="padeiro@passoca.com",
            senha_hash=hash_senha("senha-valida-123"), perfil=PerfilUsuario.PADEIRO,
        )
        db_session.add(padeiro)
        db_session.commit()
        client_anonimo.post(
            "/auth/login", json={"email": "padeiro@passoca.com", "senha": "senha-valida-123"}
        )

        resp = client_anonimo.get("/clientes/9999/pedidos")
        # 404 (não 403) — o padeiro pode ler, só que o cliente não existe
        assert resp.status_code == 404
