"""
Ponto único de importação dos models.

Importante para o Alembic: o autogenerate só enxerga uma tabela se a classe
do model tiver sido importada em algum lugar antes de `Base.metadata` ser
inspecionado. Centralizar aqui evita esquecer de registrar um model novo.
"""
from app.models.cliente import Cliente
from app.models.evento_auditoria import EventoAuditoria
from app.models.item_pedido import ItemPedido
from app.models.pedido import TRANSICOES_VALIDAS, Pedido, StatusPedido
from app.models.produto import CategoriaProduto, Produto, UnidadeProduto
from app.models.tentativa_login import TentativaLogin
from app.models.usuario import PerfilUsuario, Usuario

__all__ = [
    "TRANSICOES_VALIDAS",
    "CategoriaProduto",
    "Cliente",
    "EventoAuditoria",
    "ItemPedido",
    "Pedido",
    "PerfilUsuario",
    "Produto",
    "StatusPedido",
    "TentativaLogin",
    "UnidadeProduto",
    "Usuario",
]
