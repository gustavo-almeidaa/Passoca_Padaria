"""Ponto único de importação dos schemas Pydantic (request/response da API)."""
from app.schemas.cliente import ClienteCreate, ClienteRead
from app.schemas.pedido import ItemPedidoCreate, ItemPedidoRead, PedidoCreate, PedidoRead
from app.schemas.produto import ProdutoCreate, ProdutoRead
from app.schemas.usuario import TrocarSenhaRequest, UsuarioCreate, UsuarioLogin, UsuarioRead

__all__ = [
    "ClienteCreate",
    "ClienteRead",
    "ProdutoCreate",
    "ProdutoRead",
    "PedidoCreate",
    "PedidoRead",
    "ItemPedidoCreate",
    "ItemPedidoRead",
    "UsuarioCreate",
    "UsuarioRead",
    "UsuarioLogin",
    "TrocarSenhaRequest",
]
