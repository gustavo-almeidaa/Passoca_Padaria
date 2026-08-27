"""Model EventoAuditoria — trilha de auditoria (Incremento 18, achado A-01).

Tabela **apenas de escrita**: registra quem fez o quê, quando, e o estado
antes/depois, para toda operação que altere estado de pedido, preço de
produto ou cadastro de usuário. Nunca é atualizada nem apagada pela
aplicação.

`usuario_email` / `usuario_perfil` são *snapshots* em texto — a trilha
continua legível mesmo se o usuário for renomeado, trocar de perfil ou for
desativado.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventoAuditoria(Base):
    __tablename__ = "eventos_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Quem. FK preservada (usuários nunca são apagados, só desativados),
    # mais o snapshot em texto para a trilha sobreviver a qualquer mudança
    # no cadastro depois.
    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    usuario_email: Mapped[str] = mapped_column(String(255), nullable=False)
    usuario_perfil: Mapped[str] = mapped_column(String(20), nullable=False)

    # O quê.
    entidade: Mapped[str] = mapped_column(String(20), nullable=False)  # pedido|produto|usuario
    entidade_id: Mapped[int] = mapped_column(Integer, nullable=False)
    acao: Mapped[str] = mapped_column(String(30), nullable=False)

    # Estado antes/depois — dicts de campos relevantes. `anterior` é nulo
    # numa criação. Nunca guarda valor de senha.
    estado_anterior: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    estado_posterior: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_eventos_auditoria_criado_em", "criado_em"),
        Index("ix_eventos_auditoria_entidade", "entidade", "entidade_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<EventoAuditoria {self.entidade}:{self.entidade_id} {self.acao} "
            f"por {self.usuario_email!r}>"
        )
