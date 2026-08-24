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
    def preco_nao_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("O preço não pode ser negativo.")
        return v


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoRead(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
