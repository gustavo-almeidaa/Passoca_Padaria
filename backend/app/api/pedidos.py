"""Endpoints de Pedido — RF03/RF04 (registrar), RF05 (consultar), RF06
(cancelar) e RF07 (listar por período).

A lógica de domínio (RN01-RN04 e validações de cliente/produto) vive em
`app/services/pedidos.py`; este módulo só traduz o resultado do service para
HTTP, com mensagens em português claro (CLAUDE.md, seção 1.6).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.database import get_db
from app.models.pedido import Pedido
from app.schemas.pedido import PedidoCreate, PedidoRead
from app.services import pedidos as pedidos_service

# Incremento 12: exige login pra qualquer rota de pedido — sem restrição
# por perfil ainda (CLAUDE.md, seção 11).
router = APIRouter(
    prefix="/pedidos", tags=["pedidos"], dependencies=[Depends(get_usuario_atual)]
)


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


@router.get("", response_model=list[PedidoRead])
def listar_pedidos(
    data_inicio: date = Query(
        ..., description="Data inicial do período (obrigatória)."
    ),
    data_fim: Optional[date] = Query(
        default=None,
        description="Data final do período. Se omitida, lista só `data_inicio` (um dia).",
    ),
    db: Session = Depends(get_db),
) -> list[Pedido]:
    try:
        return pedidos_service.listar_pedidos(db, data_inicio, data_fim)
    except pedidos_service.IntervaloDeDatasInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{pedido_id}", response_model=PedidoRead)
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)) -> Pedido:
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return pedido


@router.post("/{pedido_id}/confirmar-sinal", response_model=PedidoRead)
def confirmar_sinal(pedido_id: int, db: Session = Depends(get_db)) -> Pedido:
    try:
        return pedidos_service.confirmar_sinal(db, pedido_id)
    except pedidos_service.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{pedido_id}/avancar", response_model=PedidoRead)
def avancar_pedido(pedido_id: int, db: Session = Depends(get_db)) -> Pedido:
    try:
        return pedidos_service.avancar_status(db, pedido_id)
    except pedidos_service.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        pedidos_service.SinalNaoConfirmado,
        pedidos_service.TransicaoInvalida,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{pedido_id}/cancelar", response_model=PedidoRead)
def cancelar_pedido(pedido_id: int, db: Session = Depends(get_db)) -> Pedido:
    try:
        return pedidos_service.cancelar_pedido(db, pedido_id)
    except pedidos_service.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        pedidos_service.TransicaoInvalida,
        pedidos_service.ForaDaJanelaDeCancelamento,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
