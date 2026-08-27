"""Endpoint de leitura da trilha de auditoria — Incremento 18 (A-01).

Só a proprietária consulta (mesma decisão da aba "Usuários", Incremento 15
— controle sensível não é pra qualquer perfil). A gravação da trilha
acontece em `app/services/auditoria.py`, chamada pelas operações de
negócio; aqui é só leitura.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import exigir_proprietaria
from app.core.database import get_db
from app.models.evento_auditoria import EventoAuditoria
from app.models.usuario import Usuario
from app.schemas.auditoria import EventoAuditoriaRead

router = APIRouter(
    prefix="/auditoria",
    tags=["auditoria"],
    dependencies=[Depends(exigir_proprietaria)],
)

LIMITE_PADRAO = 100
LIMITE_MAXIMO = 500


@router.get("", response_model=list[EventoAuditoriaRead])
def listar_eventos(
    db: Session = Depends(get_db),
    entidade: Optional[str] = Query(
        default=None, description="Filtra por tipo: pedido, produto ou usuario."
    ),
    entidade_id: Optional[int] = Query(
        default=None, description="Filtra pelo id do registro afetado."
    ),
    data_inicio: Optional[date] = Query(
        default=None, description="Só eventos a partir desta data (inclusive)."
    ),
    data_fim: Optional[date] = Query(
        default=None, description="Só eventos até esta data (inclusive)."
    ),
    limite: int = Query(
        default=LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO,
        description=f"Máximo de eventos retornados (teto {LIMITE_MAXIMO}).",
    ),
    _proprietaria: Usuario = Depends(exigir_proprietaria),
) -> list[EventoAuditoria]:
    consulta = db.query(EventoAuditoria)

    if entidade is not None:
        consulta = consulta.filter(EventoAuditoria.entidade == entidade)
    if entidade_id is not None:
        consulta = consulta.filter(EventoAuditoria.entidade_id == entidade_id)
    if data_inicio is not None:
        consulta = consulta.filter(
            EventoAuditoria.criado_em >= datetime.combine(data_inicio, time.min)
        )
    if data_fim is not None:
        consulta = consulta.filter(
            EventoAuditoria.criado_em <= datetime.combine(data_fim, time.max)
        )

    return (
        consulta.order_by(EventoAuditoria.criado_em.desc(), EventoAuditoria.id.desc())
        .limit(limite)
        .all()
    )
