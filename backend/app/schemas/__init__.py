"""Ponto único de importação dos schemas Pydantic (request/response da API)."""
from app.schemas.cliente import ClienteCreate, ClienteRead
from app.schemas.pedido import ItemPedidoCreate, ItemPedidoRead, PedidoCreate, PedidoRead
from app.schemas.produto import ProdutoCreate, ProdutoRead

__all__ = [
    "ClienteCreate",
    "ClienteRead",
    "ProdutoCreate",
    "ProdutoRead",
    "PedidoCreate",
    "PedidoRead",
    "ItemPedidoCreate",
    "ItemPedidoRead",
]
