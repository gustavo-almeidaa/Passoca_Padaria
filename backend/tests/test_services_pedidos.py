"""Testes do service de Pedido — RN01-RN04 isoladas de HTTP (CLAUDE.md, seção
1.5: RN merece teste automatizado dedicado, não só teste manual/via API).

Incremento 18: as funções que mudam estado recebem o `usuario` autenticado
(para a trilha de auditoria). Os testes usam a fixture `operador`.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models import CategoriaProduto, Cliente, Produto, UnidadeProduto
from app.models.item_pedido import ItemPedido
from app.models.pedido import Pedido, StatusPedido
from app.models.usuario import PerfilUsuario, Usuario
from app.schemas.pedido import ItemPedidoCreate, PedidoCreate, PedidoUpdate
from app.services import pedidos as pedidos_service


@pytest.fixture()
def operador(db_session):
    usuario = Usuario(
        nome="Atendente Op",
        email="op@passoca.com",
        senha_hash="x",
        perfil=PerfilUsuario.ATENDENTE,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


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

    def test_aceita_entrega_com_exatamente_24h_de_folga(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(hours=24)

        pedido = pedidos_service.criar_pedido(
            db_session, _payload(cliente.id, produto.id, entrega),
            usuario=operador, agora=agora,
        )

        assert pedido.id is not None
        assert pedido.data_entrega == entrega.date()

    def test_rejeita_entrega_com_menos_de_24h_de_folga(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(hours=23, minutes=59)

        with pytest.raises(pedidos_service.AntecedenciaMinimaNaoRespeitada):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega),
                usuario=operador, agora=agora,
            )

    def test_rejeita_entrega_no_passado(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora - timedelta(days=1)

        with pytest.raises(pedidos_service.AntecedenciaMinimaNaoRespeitada):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega),
                usuario=operador, agora=agora,
            )


class TestCriarPedidoAntecedenciaMaxima:
    """Teto realista de 90 dias (decisão do usuário, 2026-08-25)."""

    def test_aceita_entrega_com_exatamente_90_dias_de_folga(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=90)

        pedido = pedidos_service.criar_pedido(
            db_session, _payload(cliente.id, produto.id, entrega),
            usuario=operador, agora=agora,
        )

        assert pedido.id is not None

    def test_rejeita_entrega_com_mais_de_90_dias_de_folga(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=91)

        with pytest.raises(pedidos_service.AntecedenciaMaximaExcedida):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega),
                usuario=operador, agora=agora,
            )


class TestCriarPedidoValidacoes:
    def test_cliente_inexistente_gera_erro_especifico(self, db_session, operador):
        produto = _criar_produto(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        with pytest.raises(pedidos_service.ClienteNaoEncontrado):
            pedidos_service.criar_pedido(
                db_session, _payload(9999, produto.id, entrega),
                usuario=operador, agora=agora,
            )

    def test_produto_inexistente_gera_erro_especifico(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        with pytest.raises(pedidos_service.ProdutoInvalido):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, 9999, entrega),
                usuario=operador, agora=agora,
            )

    def test_produto_inativo_e_rejeitado(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, ativo=False)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        with pytest.raises(pedidos_service.ProdutoInvalido):
            pedidos_service.criar_pedido(
                db_session, _payload(cliente.id, produto.id, entrega),
                usuario=operador, agora=agora,
            )

    def test_preco_unitario_e_snapshot_do_produto_no_momento_da_criacao(
        self, db_session, operador
    ):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, preco=Decimal("10.00"))
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        pedido = pedidos_service.criar_pedido(
            db_session,
            _payload(cliente.id, produto.id, entrega, quantidade=3),
            usuario=operador,
            agora=agora,
        )

        assert pedido.itens[0].preco_unitario == Decimal("10.00")
        assert pedido.itens[0].quantidade == 3

    def test_pedido_criado_comeca_em_recebido_sem_sinal(self, db_session, operador):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, personalizavel=True)
        agora = datetime(2026, 1, 1, 10, 0)
        entrega = agora + timedelta(days=2)

        pedido = pedidos_service.criar_pedido(
            db_session, _payload(cliente.id, produto.id, entrega),
            usuario=operador, agora=agora,
        )

        assert pedido.status.value == "recebido"
        assert pedido.sinal_confirmado is False


def _criar_pedido_direto(
    db_session,
    *,
    personalizavel=False,
    sinal_confirmado=False,
    status=StatusPedido.RECEBIDO,
    entrega=None,
):
    """Cria um Pedido direto no banco (sem passar por `criar_pedido`), para
    testar avançar/cancelar a partir de um estado arbitrário sem depender de
    RN01 (antecedência mínima na criação).
    """
    cliente = _criar_cliente(db_session)
    produto = _criar_produto(db_session, personalizavel=personalizavel)
    entrega = entrega or datetime(2026, 1, 10, 18, 0)

    pedido = Pedido(
        cliente_id=cliente.id,
        data_entrega=entrega.date(),
        hora_entrega=entrega.time(),
        status=status,
        sinal_confirmado=sinal_confirmado,
    )
    pedido.itens = [
        ItemPedido(
            produto_id=produto.id, quantidade=1, preco_unitario=produto.preco
        )
    ]
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)
    return pedido


class TestConfirmarSinal:
    def test_confirma_sinal_de_pedido_existente(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session, personalizavel=True)

        atualizado = pedidos_service.confirmar_sinal(
            db_session, pedido.id, usuario=operador
        )

        assert atualizado.sinal_confirmado is True

    def test_pedido_inexistente_gera_erro_especifico(self, db_session, operador):
        with pytest.raises(pedidos_service.PedidoNaoEncontrado):
            pedidos_service.confirmar_sinal(db_session, 9999, usuario=operador)


class TestAvancarStatusRN02RN04:
    """RN02 (sinal obrigatório) e RN04 (máquina de estados) em `avancar_status`."""

    def test_avanca_recebido_para_em_producao_sem_item_personalizavel(
        self, db_session, operador
    ):
        pedido = _criar_pedido_direto(db_session, personalizavel=False)

        atualizado = pedidos_service.avancar_status(
            db_session, pedido.id, usuario=operador
        )

        assert atualizado.status == StatusPedido.EM_PRODUCAO

    def test_rejeita_avanco_com_item_personalizavel_sem_sinal(self, db_session, operador):
        pedido = _criar_pedido_direto(
            db_session, personalizavel=True, sinal_confirmado=False
        )

        with pytest.raises(pedidos_service.SinalNaoConfirmado):
            pedidos_service.avancar_status(db_session, pedido.id, usuario=operador)

        assert pedido.status == StatusPedido.RECEBIDO

    def test_aceita_avanco_com_item_personalizavel_e_sinal_confirmado(
        self, db_session, operador
    ):
        pedido = _criar_pedido_direto(
            db_session, personalizavel=True, sinal_confirmado=True
        )

        atualizado = pedidos_service.avancar_status(
            db_session, pedido.id, usuario=operador
        )

        assert atualizado.status == StatusPedido.EM_PRODUCAO

    def test_avanca_em_producao_para_pronto(self, db_session, operador):
        pedido = _criar_pedido_direto(
            db_session, status=StatusPedido.EM_PRODUCAO
        )

        atualizado = pedidos_service.avancar_status(
            db_session, pedido.id, usuario=operador
        )

        assert atualizado.status == StatusPedido.PRONTO

    def test_avanca_pronto_para_entregue(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session, status=StatusPedido.PRONTO)

        atualizado = pedidos_service.avancar_status(
            db_session, pedido.id, usuario=operador
        )

        assert atualizado.status == StatusPedido.ENTREGUE

    def test_rejeita_avanco_de_pedido_entregue(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session, status=StatusPedido.ENTREGUE)

        with pytest.raises(pedidos_service.TransicaoInvalida):
            pedidos_service.avancar_status(db_session, pedido.id, usuario=operador)

    def test_rejeita_avanco_de_pedido_cancelado(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session, status=StatusPedido.CANCELADO)

        with pytest.raises(pedidos_service.TransicaoInvalida):
            pedidos_service.avancar_status(db_session, pedido.id, usuario=operador)

    def test_pedido_inexistente_gera_erro_especifico(self, db_session, operador):
        with pytest.raises(pedidos_service.PedidoNaoEncontrado):
            pedidos_service.avancar_status(db_session, 9999, usuario=operador)


class TestCancelarPedidoRN03RN04:
    """RN03 (janela de 12h) e RN04 (só a partir de recebido/em_producao)."""

    def test_cancela_pedido_recebido_dentro_da_janela(self, db_session, operador):
        agora = datetime(2026, 1, 10, 6, 0)
        entrega = agora + timedelta(hours=12, minutes=1)
        pedido = _criar_pedido_direto(db_session, entrega=entrega)

        atualizado = pedidos_service.cancelar_pedido(
            db_session, pedido.id, usuario=operador, agora=agora
        )

        assert atualizado.status == StatusPedido.CANCELADO

    def test_cancela_pedido_em_producao_dentro_da_janela(self, db_session, operador):
        agora = datetime(2026, 1, 10, 6, 0)
        entrega = agora + timedelta(hours=13)
        pedido = _criar_pedido_direto(
            db_session, status=StatusPedido.EM_PRODUCAO, entrega=entrega
        )

        atualizado = pedidos_service.cancelar_pedido(
            db_session, pedido.id, usuario=operador, agora=agora
        )

        assert atualizado.status == StatusPedido.CANCELADO

    def test_rejeita_cancelamento_com_menos_de_12h_de_folga(self, db_session, operador):
        agora = datetime(2026, 1, 10, 6, 0)
        entrega = agora + timedelta(hours=11, minutes=59)
        pedido = _criar_pedido_direto(db_session, entrega=entrega)

        with pytest.raises(pedidos_service.ForaDaJanelaDeCancelamento):
            pedidos_service.cancelar_pedido(
                db_session, pedido.id, usuario=operador, agora=agora
            )

        assert pedido.status == StatusPedido.RECEBIDO

    def test_aceita_cancelamento_com_exatamente_12h_de_folga(self, db_session, operador):
        # RN03 exige "agora <= data_entrega - 12h" — a igualdade é o limite
        # aceito (ver test_rejeita_cancelamento_com_menos_de_12h_de_folga
        # para o caso logo abaixo do limite).
        agora = datetime(2026, 1, 10, 6, 0)
        entrega = agora + timedelta(hours=12)
        pedido = _criar_pedido_direto(db_session, entrega=entrega)

        atualizado = pedidos_service.cancelar_pedido(
            db_session, pedido.id, usuario=operador, agora=agora
        )

        assert atualizado.status == StatusPedido.CANCELADO

    def test_rejeita_cancelamento_de_pedido_pronto(self, db_session, operador):
        pedido = _criar_pedido_direto(
            db_session,
            status=StatusPedido.PRONTO,
            entrega=datetime(2026, 1, 10, 18, 0),
        )

        with pytest.raises(pedidos_service.TransicaoInvalida):
            pedidos_service.cancelar_pedido(
                db_session, pedido.id, usuario=operador, agora=datetime(2026, 1, 1, 6, 0)
            )

    def test_rejeita_cancelamento_de_pedido_ja_cancelado(self, db_session, operador):
        pedido = _criar_pedido_direto(
            db_session,
            status=StatusPedido.CANCELADO,
            entrega=datetime(2026, 1, 10, 18, 0),
        )

        with pytest.raises(pedidos_service.TransicaoInvalida):
            pedidos_service.cancelar_pedido(
                db_session, pedido.id, usuario=operador, agora=datetime(2026, 1, 1, 6, 0)
            )

    def test_pedido_inexistente_gera_erro_especifico(self, db_session, operador):
        with pytest.raises(pedidos_service.PedidoNaoEncontrado):
            pedidos_service.cancelar_pedido(db_session, 9999, usuario=operador)


def _update(pedido, *, itens=None, entrega=None):
    """Monta um PedidoUpdate a partir do estado atual do pedido, trocando só
    o que for passado."""
    entrega = entrega or datetime.combine(pedido.data_entrega, pedido.hora_entrega)
    if itens is None:
        itens = [
            ItemPedidoCreate(produto_id=i.produto_id, quantidade=i.quantidade)
            for i in pedido.itens
        ]
    return PedidoUpdate(
        data_entrega=entrega.date(),
        hora_entrega=entrega.time(),
        itens=itens,
    )


class TestEditarPedido:
    """Incremento 23 — editar itens e/ou data de entrega de um pedido em
    `recebido`. Regras confirmadas com o usuário em 2026-08-27."""

    AGORA = datetime(2026, 1, 8, 10, 0)  # bem antes da entrega padrão (dia 10)

    def test_edita_quantidade_de_item(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        produto_id = pedido.itens[0].produto_id

        atualizado = pedidos_service.editar_pedido(
            db_session,
            pedido.id,
            _update(pedido, itens=[ItemPedidoCreate(produto_id=produto_id, quantidade=7)]),
            usuario=operador,
            agora=self.AGORA,
        )

        assert atualizado.itens[0].quantidade == 7

    def test_edita_data_de_entrega(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        nova = datetime(2026, 1, 15, 9, 0)

        atualizado = pedidos_service.editar_pedido(
            db_session, pedido.id, _update(pedido, entrega=nova),
            usuario=operador, agora=self.AGORA,
        )

        assert atualizado.data_entrega == nova.date()
        assert atualizado.hora_entrega == nova.time()

    def test_item_que_ja_existia_mantem_preco_travado(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        produto = db_session.get(Produto, pedido.itens[0].produto_id)
        preco_original = pedido.itens[0].preco_unitario
        produto.preco = Decimal("999.00")  # reajuste do cardápio depois
        db_session.commit()

        atualizado = pedidos_service.editar_pedido(
            db_session, pedido.id,
            _update(pedido, itens=[ItemPedidoCreate(produto_id=produto.id, quantidade=3)]),
            usuario=operador, agora=self.AGORA,
        )

        assert atualizado.itens[0].preco_unitario == preco_original

    def test_item_novo_pega_preco_atual(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        pao = _criar_produto(db_session, nome="Pão", preco=Decimal("6.50"))

        atualizado = pedidos_service.editar_pedido(
            db_session, pedido.id,
            _update(pedido, itens=[
                ItemPedidoCreate(produto_id=pedido.itens[0].produto_id, quantidade=1),
                ItemPedidoCreate(produto_id=pao.id, quantidade=2),
            ]),
            usuario=operador, agora=self.AGORA,
        )

        item_pao = next(i for i in atualizado.itens if i.produto_id == pao.id)
        assert item_pao.preco_unitario == Decimal("6.50")

    def test_rejeita_edicao_de_pedido_em_producao(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session, status=StatusPedido.EM_PRODUCAO)

        with pytest.raises(pedidos_service.PedidoNaoEditavel):
            pedidos_service.editar_pedido(
                db_session, pedido.id, _update(pedido), usuario=operador, agora=self.AGORA
            )

    def test_rejeita_edicao_de_pedido_entregue(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session, status=StatusPedido.ENTREGUE)

        with pytest.raises(pedidos_service.PedidoNaoEditavel):
            pedidos_service.editar_pedido(
                db_session, pedido.id, _update(pedido), usuario=operador, agora=self.AGORA
            )

    def test_pedido_inexistente_gera_erro_especifico(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        with pytest.raises(pedidos_service.PedidoNaoEncontrado):
            pedidos_service.editar_pedido(
                db_session, 9999, _update(pedido), usuario=operador, agora=self.AGORA
            )

    def test_nova_data_revalida_rn01(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        # agora = dia 8; remarcar pra dia 8 + 12h fere a antecedência de 24h
        with pytest.raises(pedidos_service.AntecedenciaMinimaNaoRespeitada):
            pedidos_service.editar_pedido(
                db_session, pedido.id,
                _update(pedido, entrega=self.AGORA + timedelta(hours=12)),
                usuario=operador, agora=self.AGORA,
            )

    def test_nova_data_revalida_rn05(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        with pytest.raises(pedidos_service.AntecedenciaMaximaExcedida):
            pedidos_service.editar_pedido(
                db_session, pedido.id,
                _update(pedido, entrega=self.AGORA + timedelta(days=91)),
                usuario=operador, agora=self.AGORA,
            )

    def test_produto_inativo_e_rejeitado(self, db_session, operador):
        pedido = _criar_pedido_direto(db_session)
        inativo = _criar_produto(db_session, nome="Fora de linha", ativo=False)

        with pytest.raises(pedidos_service.ProdutoInvalido):
            pedidos_service.editar_pedido(
                db_session, pedido.id,
                _update(pedido, itens=[ItemPedidoCreate(produto_id=inativo.id, quantidade=1)]),
                usuario=operador, agora=self.AGORA,
            )

    def test_adicionar_item_personalizavel_reseta_o_sinal(self, db_session, operador):
        pedido = _criar_pedido_direto(
            db_session, personalizavel=True, sinal_confirmado=True
        )
        base_id = pedido.itens[0].produto_id
        # muda a quantidade do item personalizável -> composição mudou
        atualizado = pedidos_service.editar_pedido(
            db_session, pedido.id,
            _update(pedido, itens=[ItemPedidoCreate(produto_id=base_id, quantidade=2)]),
            usuario=operador, agora=self.AGORA,
        )

        assert atualizado.sinal_confirmado is False

    def test_editar_so_a_data_nao_reseta_o_sinal(self, db_session, operador):
        pedido = _criar_pedido_direto(
            db_session, personalizavel=True, sinal_confirmado=True
        )
        atualizado = pedidos_service.editar_pedido(
            db_session, pedido.id,
            _update(pedido, entrega=datetime(2026, 1, 16, 10, 0)),
            usuario=operador, agora=self.AGORA,
        )

        assert atualizado.sinal_confirmado is True

    def test_registra_evento_de_auditoria(self, db_session, operador):
        from app.models.evento_auditoria import EventoAuditoria

        pedido = _criar_pedido_direto(db_session)
        pedidos_service.editar_pedido(
            db_session, pedido.id,
            _update(pedido, entrega=datetime(2026, 1, 17, 10, 0)),
            usuario=operador, agora=self.AGORA,
        )

        evento = (
            db_session.query(EventoAuditoria)
            .filter(EventoAuditoria.acao == "editar", EventoAuditoria.entidade == "pedido")
            .one()
        )
        assert evento.usuario_email == operador.email
        assert evento.estado_anterior["data_entrega"] != evento.estado_posterior["data_entrega"]


class TestListarPedidosRF07:
    def test_lista_pedidos_dentro_do_periodo(self, db_session):
        dentro = _criar_pedido_direto(
            db_session, entrega=datetime(2026, 1, 10, 12, 0)
        )
        fora = _criar_pedido_direto(
            db_session, entrega=datetime(2026, 1, 20, 12, 0)
        )

        resultado = pedidos_service.listar_pedidos(
            db_session, date(2026, 1, 9), date(2026, 1, 11)
        )

        ids = {p.id for p in resultado}
        assert dentro.id in ids
        assert fora.id not in ids

    def test_sem_data_fim_lista_apenas_o_dia_de_data_inicio(self, db_session):
        pedido = _criar_pedido_direto(
            db_session, entrega=datetime(2026, 1, 10, 12, 0)
        )

        resultado = pedidos_service.listar_pedidos(db_session, date(2026, 1, 10))

        assert [p.id for p in resultado] == [pedido.id]

    def test_data_fim_anterior_a_data_inicio_e_rejeitada(self, db_session):
        with pytest.raises(pedidos_service.IntervaloDeDatasInvalido):
            pedidos_service.listar_pedidos(
                db_session, date(2026, 1, 10), date(2026, 1, 5)
            )

    def test_listar_nao_faz_n_mais_1_ao_carregar_itens(self, db_session):
        """Incremento 22 (A-07): a listagem carrega os itens com selectinload
        — sem isso, cada pedido do dia dispara uma query separada (N+1), o
        que contra o Postgres do Neon vira segundos."""
        from sqlalchemy import event

        for _ in range(5):
            _criar_pedido_direto(db_session, entrega=datetime(2026, 1, 10, 12, 0))

        engine = db_session.get_bind()
        selects: list[str] = []

        def _contar(conn, cursor, statement, params, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                selects.append(statement)

        event.listen(engine, "before_cursor_execute", _contar)
        try:
            resultado = pedidos_service.listar_pedidos(db_session, date(2026, 1, 10))
            _ = [list(pedido.itens) for pedido in resultado]  # força serialização
        finally:
            event.remove(engine, "before_cursor_execute", _contar)

        assert len(resultado) == 5
        # 1 query pros pedidos + 1 pros itens. Sem selectinload seriam 6.
        assert len(selects) <= 2
