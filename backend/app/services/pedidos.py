"""Service de Pedido — RF03/RF04, aplicando RN01 no backend.

Regra de negócio crítica (CLAUDE.md, seção 1.4: "RN01-RN04 são validadas no
backend, sempre") vive aqui, fora do endpoint FastAPI, para poder ser testada
isoladamente sem precisar subir a camada HTTP.

Exceções específicas por tipo de falha (em vez de uma genérica) permitem que
a camada de API escolha o status HTTP e a mensagem certos para cada caso —
ver `app/api/pedidos.py`.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.item_pedido import ItemPedido
from app.models.pedido import Pedido
from app.models.produto import Produto
from app.schemas.pedido import PedidoCreate

# RN01 — antecedência mínima entre a criação do pedido e a data/hora de entrega.
ANTECEDENCIA_MINIMA = timedelta(hours=24)


class ClienteNaoEncontrado(Exception):
    """Pedido referencia um cliente que não existe no cadastro."""


class ProdutoInvalido(Exception):
    """Item do pedido referencia um produto inexistente ou indisponível."""

    def __init__(self, produto_id: int, motivo: str):
        self.produto_id = produto_id
        super().__init__(motivo)


class AntecedenciaMinimaNaoRespeitada(Exception):
    """RN01: entrega marcada com menos de 24h de antecedência."""


def criar_pedido(
    db: Session, payload: PedidoCreate, *, agora: datetime | None = None
) -> Pedido:
    """Cria um pedido (RF03) com data/hora de entrega (RF04), aplicando RN01.

    `agora` é injetável para permitir testes determinísticos da janela de
    24h (RN01) sem depender do relógio real da máquina que roda o teste.
    """
    agora = agora or datetime.now()

    cliente = db.get(Cliente, payload.cliente_id)
    if cliente is None:
        raise ClienteNaoEncontrado(f"Cliente {payload.cliente_id} não encontrado.")

    momento_entrega = datetime.combine(payload.data_entrega, payload.hora_entrega)
    if momento_entrega - agora < ANTECEDENCIA_MINIMA:
        raise AntecedenciaMinimaNaoRespeitada(
            "Escolha uma data e horário de entrega com pelo menos 24h de "
            "antecedência a partir de agora."
        )

    itens: list[ItemPedido] = []
    for item_in in payload.itens:
        produto = db.get(Produto, item_in.produto_id)
        if produto is None:
            raise ProdutoInvalido(
                item_in.produto_id,
                f"Produto {item_in.produto_id} não encontrado.",
            )
        if not produto.ativo:
            raise ProdutoInvalido(
                item_in.produto_id,
                f'Produto "{produto.nome}" não está mais disponível para encomenda.',
            )
        itens.append(
            ItemPedido(
                produto_id=produto.id,
                quantidade=item_in.quantidade,
                # Snapshot do preço atual — não deve mudar se o cardápio
                # for reajustado depois (ver app/models/item_pedido.py).
                preco_unitario=produto.preco,
            )
        )

    pedido = Pedido(
        cliente_id=cliente.id,
        data_entrega=payload.data_entrega,
        hora_entrega=payload.hora_entrega,
        itens=itens,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido
