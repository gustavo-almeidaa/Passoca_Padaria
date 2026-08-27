"""Schema Pydantic da trilha de auditoria — Incremento 18 (A-01)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventoAuditoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    usuario_id: Optional[int]
    usuario_email: str
    usuario_perfil: str
    entidade: str
    entidade_id: int
    acao: str
    estado_anterior: Optional[dict]
    estado_posterior: Optional[dict]
