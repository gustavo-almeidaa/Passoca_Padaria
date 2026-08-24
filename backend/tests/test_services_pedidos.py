"""Testes do service de Pedido — RN01 isolada de HTTP (CLAUDE.md, seção 1.5:
RN merece teste automatizado dedicado, não só teste manual/via API).
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models import CategoriaProduto, Cliente, Produto, UnidadeProduto
from app.schemas.pedido import ItemPedidoCreate, PedidoCreate
from app.services import pedidos as pedidos_service


def _criar_cliente(db_session, nome="Maria Silva", telefone="43999990000"):
    cliente = Cliente(nome=nome, telefone=telefone)
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


def _criar_produto(
    db_session,
    nome="Bolo de chocolate",
    preco=Decimal("45.00"),
    personalizavel=False,
    ativo=True,
):
    produto = Produto(
        nome=nome,
        categoria=CategoriaProduto.BOLO,
        unidade=UnidadeProduto.UNIDADE,
        preco=preco,
        personalizavel=personalizavel,
        ativo=ativo,
    )
    db_session.add(produto)
    db_session.commit()
    db_session.refresh(produto)
    return produto


def _payload(cliente_id, produto_id, entrega, quantidade=1):
    return PedidoCreate(
        cliente_id=cliente_id,
        data_entrega=entrega.date(),
        hora_entrega=entrega.time(),
        itens=[ItemPedidoCreate(produto_id=produto_id, quantidade=quantidade)],
    )


class TestCriarPedidoRN01:
    """RN01 — antecedência mínima de 24h entre `agora` e a entrega."""

    def test_aceita_entrega_com_exatamente_24h_de_folga(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(hours=24)

        pedido = pedidos_service.criar_pedido(
            db_session, _payload(cliente.id, produto.id, entrega), agora=agora
        )

        assert pedido.id is not None
        assert pedido.data_entrega == entrega.date()

    def test_rejeita_entrega_com_menos_de_24h_de_folga(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(hours=23, minutes=59)

        with pytest.raises(pedidos_service.AntecedenciaMinimaNaoRespeitada):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega), agora=agora
            )

    def test_rejeita_entrega_no_passado(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora - timedelta(days=1)

        with pytest.raises(pedidos_service.AntecedenciaMinimaNaoRespeitada):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega), agora=agora
            )


class TestCriarPedidoValidacoes:
    def test_cliente_inexistente_gera_erro_especifico(self, db_session):
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        with pytest.raises(pedidos_service.ClienteNaoEncontrado):
            pedidos_service.criar_pedido(
                db_session, _payload(9999, produto.id, entrega), agora=agora
            )

    def test_produto_inexistente_gera_erro_especifico(self, db_session):
        cliente = _criar_cliente(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        with pytest.raises(pedidos_service.ProdutoInvalido):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, 9999, entrega), agora=agora
            )

    def test_produto_inativo_e_rejeitado(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, ativo=False)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        with pytest.raises(pedidos_service.ProdutoInvalido):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega), agora=agora
            )

    def test_preco_unitario_e_snapshot_do_produto_no_momento_da_criacao(
        self, db_session
    ):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, preco=Decimal("10.00"))
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        pedido = pedidos_service.criar_pedido(
            db_session,
            _payload(cliente.id, produto.id, entrega, quantidade=3),
            agora=agora,
        )

        assert pedido.itens[0].preco_unitario == Decimal("10.00")
        assert pedido.itens[0].quantidade == 3

    def test_pedido_criado_comeca_em_recebido_sem_sinal(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, personalizavel=True)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        pedido = pedidos_service.criar_pedido(
            db_session, _payload(cliente.id, produto.id, entrega), agora=agora
        )

        assert pedido.status.value == "recebido"
        assert pedido.sinal_confirmado is False
