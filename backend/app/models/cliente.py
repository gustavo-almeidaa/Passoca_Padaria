"""Model Cliente — RF01 (cadastrar cliente)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.pedido import Pedido


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Sem cascade de delete: não existe RF de exclusão de cliente, e um
    # pedido é registro de negócio — não deve desaparecer se um dia essa
    # funcionalidade for adicionada sem cuidado extra.
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")

    def __repr__(self) -> str:
        return f"<Cliente id={self.id} nome={self.nome!r}>"
