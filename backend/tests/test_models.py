"""
Testes do Incremento 1: schema, relacionamentos e constraints de banco.

Este incremento não inclui a lógica de domínio das RNs (isso é
responsabilidade da camada de services, no Incremento 2) — aqui testamos
que o *schema em si* está correto: campos obrigatórios, relacionamentos,
constraints de integridade e a máquina de estados documentada em
TRANSICOES_VALIDAS.
"""
from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    TRANSICOES_VALIDAS,
    CategoriaProduto,
    Cliente,
    ItemPedido,
    PerfilUsuario,
    Pedido,
    Produto,
    StatusPedido,
    UnidadeProduto,
    Usuario,
)


def _criar_cliente(db_session, nome="Maria Silva", telefone="43999990000"):
    cliente = Cliente(nome=nome, telefone=telefone)
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


def _criar_produto(
    db_session,
    nome="Bolo de chocolate",
    categoria=CategoriaProduto.BOLO,
    unidade=UnidadeProduto.UNIDADE,
    preco=Decimal("45.00"),
    personalizavel=False,
):
    produto = Produto(
        nome=nome,
        categoria=categoria,
        unidade=unidade,
        preco=preco,
        personalizavel=personalizavel,
    )
    db_session.add(produto)
    db_session.commit()
    db_session.refresh(produto)
    return produto


class TestCliente:
    def test_cria_cliente_com_campos_obrigatorios(self, db_session):
        cliente = _criar_cliente(db_session)

        assert cliente.id is not None
        assert cliente.nome == "Maria Silva"
        assert cliente.telefone == "43999990000"
        assert cliente.endereco is None
        assert cliente.criado_em is not None

    def test_nome_e_obrigatorio(self, db_session):
        cliente = Cliente(telefone="43999990000")
        db_session.add(cliente)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_endereco_e_opcional_mas_pode_ser_preenchido(self, db_session):
        cliente = Cliente(
            nome="Maria Silva",
            telefone="43999990000",
            endereco="Rua das Flores, 123",
        )
        db_session.add(cliente)
        db_session.commit()
        db_session.refresh(cliente)

        assert cliente.endereco == "Rua das Flores, 123"


class TestUsuario:
    def test_cria_usuario_com_campos_obrigatorios(self, db_session):
        usuario = Usuario(
            nome="Proprietária",
            email="dona@passoca.com",
            senha_hash="hash-fake-so-pro-teste",
            perfil=PerfilUsuario.PROPRIETARIA,
        )
        db_session.add(usuario)
        db_session.commit()
        db_session.refresh(usuario)

        assert usuario.id is not None
        assert usuario.ativo is True
        assert usuario.criado_em is not None

    def test_email_e_unico(self, db_session):
        db_session.add(
            Usuario(
                nome="Proprietária",
                email="dona@passoca.com",
                senha_hash="hash-fake",
                perfil=PerfilUsuario.PROPRIETARIA,
            )
        )
        db_session.commit()

        db_session.add(
            Usuario(
                nome="Outra Pessoa",
                email="dona@passoca.com",
                senha_hash="hash-fake-2",
                perfil=PerfilUsuario.ATENDENTE,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestProduto:
    def test_cria_produto_padrao_nao_personalizavel(self, db_session):
        produto = _criar_produto(db_session)

        assert produto.personalizavel is False
        assert produto.ativo is True
        assert produto.preco == Decimal("45.00")

    def test_produto_personalizavel(self, db_session):
        produto = _criar_produto(
            db_session, nome="Bolo de festa personalizado", personalizavel=True
        )
        assert produto.personalizavel is True

    def test_preco_negativo_e_rejeitado(self, db_session):
        produto = Produto(
            nome="Produto inválido",
            categoria=CategoriaProduto.OUTRO,
            unidade=UnidadeProduto.UNIDADE,
            preco=Decimal("-10.00"),
        )
        db_session.add(produto)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestPedido:
    def test_cria_pedido_com_status_recebido_por_padrao(self, db_session):
        cliente = _criar_cliente(db_session)
        pedido = Pedido(
            cliente_id=cliente.id,
            data_entrega=date(2026, 12, 25),
            hora_entrega=time(14, 0),
        )
        db_session.add(pedido)
        db_session.commit()
        db_session.refresh(pedido)

        assert pedido.status == StatusPedido.RECEBIDO
        assert pedido.sinal_confirmado is False
        assert pedido.cliente.nome == cliente.nome

    def test_pedido_acessa_itens_via_relacionamento(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        pedido = Pedido(
            cliente_id=cliente.id,
            data_entrega=date(2026, 12, 25),
            hora_entrega=time(14, 0),
        )
        db_session.add(pedido)
        db_session.commit()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=2,
            preco_unitario=produto.preco,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(pedido)

        assert len(pedido.itens) == 1
        assert pedido.itens[0].produto.nome == produto.nome
        assert pedido.itens[0].quantidade == 2


class TestItemPedido:
    def test_quantidade_zero_ou_negativa_e_rejeitada(self, db_session):
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session)
        pedido = Pedido(
            cliente_id=cliente.id,
            data_entrega=date(2026, 12, 25),
            hora_entrega=time(14, 0),
        )
        db_session.add(pedido)
        db_session.commit()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=0,
            preco_unitario=produto.preco,
        )
        db_session.add(item)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_preco_unitario_e_snapshot_independente_do_produto(self, db_session):
        """O preço do item não deve mudar se o preço do produto mudar depois."""
        cliente = _criar_cliente(db_session)
        produto = _criar_produto(db_session, preco=Decimal("10.00"))
        pedido = Pedido(
            cliente_id=cliente.id,
            data_entrega=date(2026, 12, 25),
            hora_entrega=time(14, 0),
        )
        db_session.add(pedido)
        db_session.commit()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=1,
            preco_unitario=produto.preco,
        )
        db_session.add(item)
        db_session.commit()

        # Preço do produto muda depois (reajuste de cardápio)
        produto.preco = Decimal("15.00")
        db_session.commit()
        db_session.refresh(item)

        assert item.preco_unitario == Decimal("10.00")


class TestMaquinaDeEstados:
    """Documenta e testa RN04 no nível do dicionário de transições válidas.

    A aplicação da regra (impedir de fato uma transição inválida) é do
    service de pedidos, no Incremento 2 — aqui garantimos que o mapa de
    transições em si está correto, já que é a fonte da verdade que o
    service vai consultar.
    """

    def test_recebido_avanca_para_em_producao_ou_cancelado(self):
        assert TRANSICOES_VALIDAS[StatusPedido.RECEBIDO] == {
            StatusPedido.EM_PRODUCAO,
            StatusPedido.CANCELADO,
        }

    def test_em_producao_avanca_para_pronto_ou_cancelado(self):
        assert TRANSICOES_VALIDAS[StatusPedido.EM_PRODUCAO] == {
            StatusPedido.PRONTO,
            StatusPedido.CANCELADO,
        }

    def test_pronto_so_avanca_para_entregue(self):
        assert TRANSICOES_VALIDAS[StatusPedido.PRONTO] == {StatusPedido.ENTREGUE}

    def test_entregue_e_cancelado_sao_estados_finais(self):
        assert TRANSICOES_VALIDAS[StatusPedido.ENTREGUE] == set()
        assert TRANSICOES_VALIDAS[StatusPedido.CANCELADO] == set()

    def test_nao_e_possivel_pular_de_recebido_direto_para_entregue(self):
        assert StatusPedido.ENTREGUE not in TRANSICOES_VALIDAS[StatusPedido.RECEBIDO]

    def test_cancelado_so_e_alcancavel_de_recebido_ou_em_producao(self):
        estados_que_alcancam_cancelado = {
            estado
            for estado, destinos in TRANSICOES_VALIDAS.items()
            if StatusPedido.CANCELADO in destinos
        }
        assert estados_que_alcancam_cancelado == {
            StatusPedido.RECEBIDO,
            StatusPedido.EM_PRODUCAO,
        }
