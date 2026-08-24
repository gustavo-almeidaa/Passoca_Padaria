"""Ponto único de importação dos routers da API."""
from app.api import clientes, produtos

__all__ = ["clientes", "produtos"]
