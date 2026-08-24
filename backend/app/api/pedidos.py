"""Endpoints de Pedido — RF03 (registrar pedido) e RF04 (definir entrega).

A lógica de domínio (RN01 e validações de cliente/produto) vive em
`app/services/pedidos.py`; este módulo só traduz o resultado do service para
HTTP, com mensagens em português claro (CLAUDE.md, seção 1.6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pedido import Pedido
from app.schemas.pedido import PedidoCreate, PedidoRead
from app.services import pedidos as pedidos_service

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def criar_pedido(payload: PedidoCreate, db: Session = Depends(get_db)) -> Pedido:
    try:
        return pedidos_service.criar_pedido(db, payload)
    except pedidos_service.ClienteNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        pedidos_service.ProdutoInvalido,
        pedidos_service.AntecedenciaMinimaNaoRespeitada,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{pedido_id}", response_model=PedidoRead)
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)) -> Pedido:
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return pedido
