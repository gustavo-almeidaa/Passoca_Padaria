"""Ponto único de importação dos routers da API."""
from app.api import clientes, pedidos, produtos

__all__ = ["clientes", "pedidos", "produtos"]
