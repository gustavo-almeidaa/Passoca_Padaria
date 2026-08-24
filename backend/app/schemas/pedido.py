"""Schemas Pydantic de Pedido — RF03 (registrar pedido) e RF04 (definir entrega).

RN01 (antecedência mínima de 24h) e a validação de cliente/produto não são
verificáveis só com os tipos do payload — vivem no service (`app/services/pedidos.py`),
que é a fonte da verdade. Aqui só as validações de formato do próprio dado.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.pedido import StatusPedido


class ItemPedidoCreate(BaseModel):
    produto_id: int
    quantidade: int

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("A quantidade de cada item precisa ser maior que zero.")
        return v


class ItemPedidoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal


class PedidoCreate(BaseModel):
    cliente_id: int
    data_entrega: date
    hora_entrega: time
    itens: list[ItemPedidoCreate]

    @field_validator("itens")
    @classmethod
    def itens_nao_vazio(cls, v: list[ItemPedidoCreate]) -> list[ItemPedidoCreate]:
        if not v:
            raise ValueError("O pedido precisa ter pelo menos um item.")
        return v


class PedidoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    data_entrega: date
    hora_entrega: time
    status: StatusPedido
    sinal_confirmado: bool
    criado_em: datetime
    atualizado_em: datetime
    itens: list[ItemPedidoRead]
