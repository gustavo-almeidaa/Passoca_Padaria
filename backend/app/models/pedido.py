"""Model Pedido — RF03/RF04/RF05/RF06/RF07.

A validação das transições de status (RN04), da antecedência mínima (RN01),
da janela de cancelamento (RN03) e da exigência de sinal para itens
personalizáveis (RN02) é lógica de domínio e vive na camada de services
(Incremento 2+) — aqui só o schema e o enum de status, que já documenta as
transições válidas.
"""
from __future__ import annotations

import enum
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Time, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.item_pedido import ItemPedido


class StatusPedido(str, enum.Enum):
    RECEBIDO = "recebido"
    EM_PRODUCAO = "em_producao"
    PRONTO = "pronto"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"


# Transições válidas da máquina de estados (RN04). Vive aqui, junto ao model,
# porque é a fonte da verdade sobre o que o campo `status` pode assumir — a
# validação em si (impedir salvar uma transição inválida) é responsabilidade
# do service de pedidos.
TRANSICOES_VALIDAS: dict[StatusPedido, set[StatusPedido]] = {
    StatusPedido.RECEBIDO: {StatusPedido.EM_PRODUCAO, StatusPedido.CANCELADO},
    StatusPedido.EM_PRODUCAO: {StatusPedido.PRONTO, StatusPedido.CANCELADO},
    StatusPedido.PRONTO: {StatusPedido.ENTREGUE},
    StatusPedido.ENTREGUE: set(),
    StatusPedido.CANCELADO: set(),
}


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        Index("ix_pedidos_data_entrega", "data_entrega"),
        Index("ix_pedidos_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id"), nullable=False
    )
    data_entrega: Mapped[date] = mapped_column(Date, nullable=False)
    hora_entrega: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[StatusPedido] = mapped_column(
        SAEnum(StatusPedido, native_enum=False, length=20),
        nullable=False,
        default=StatusPedido.RECEBIDO,
    )
    # Relevante quando o pedido tem item personalizavel=true (RN02).
    sinal_confirmado: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="pedidos")
    itens: Mapped[list["ItemPedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Pedido id={self.id} status={self.status.value}>"
