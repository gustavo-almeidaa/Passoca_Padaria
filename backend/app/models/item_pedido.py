"""Model ItemPedido — item de um pedido (produto + quantidade), parte de RF03."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.pedido import Pedido
    from app.models.produto import Produto


class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_itens_pedido_quantidade_positiva"),
        CheckConstraint(
            "preco_unitario >= 0", name="ck_itens_pedido_preco_nao_negativo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)

    # Snapshot do preço no momento do pedido — não deve mudar se o preço do
    # produto for reajustado depois (histórico de venda tem que refletir o
    # que foi cobrado de fato, não o preço atual do cadastro).
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship(back_populates="itens_pedido")

    def __repr__(self) -> str:
        return f"<ItemPedido id={self.id} produto_id={self.produto_id} qtd={self.quantidade}>"
