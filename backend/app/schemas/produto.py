"""Schemas Pydantic de Produto — RF02 (cadastrar produto disponível para encomenda)."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.produto import CategoriaProduto, UnidadeProduto


class ProdutoBase(BaseModel):
    nome: str
    categoria: CategoriaProduto
    unidade: UnidadeProduto
    preco: Decimal
    # Dispara RN02 (exige sinal_confirmado) quando o produto entra em um
    # pedido — a regra em si é aplicada no service de Pedido (Incremento 3).
    personalizavel: bool = False
    ativo: bool = True

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o nome do produto.")
        return v

    @field_validator("preco")
    @classmethod
    def preco_dentro_do_limite(cls, v: Decimal) -> Decimal:
        # Teto realista (decisão do usuário, 2026-08-25) — evita erro de
        # digitação (zero a mais) virar um preço absurdo no cardápio.
        if v < 0:
            raise ValueError("O preço não pode ser negativo.")
        if v > Decimal("999.99"):
            raise ValueError("O preço não pode passar de R$ 999,99.")
        return v


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoRead(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
