"""Model Produto — RF02 (cadastrar produto disponível para encomenda)."""
from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.item_pedido import ItemPedido


class CategoriaProduto(str, enum.Enum):
    PAO = "pao"
    BOLO = "bolo"
    SALGADO = "salgado"
    DOCE = "doce"
    OUTRO = "outro"


class UnidadeProduto(str, enum.Enum):
    UNIDADE = "unidade"
    KG = "kg"
    DUZIA = "duzia"
    CENTO = "cento"


class Produto(Base):
    __tablename__ = "produtos"
    __table_args__ = (
        CheckConstraint("preco >= 0", name="ck_produtos_preco_nao_negativo"),
        # Teto realista (decisão do usuário, 2026-08-25) — defesa em
        # profundidade: o schema Pydantic já valida isso, mas o constraint
        # no banco garante mesmo se algo escrever direto via SQL/script.
        CheckConstraint("preco <= 999.99", name="ck_produtos_preco_teto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria: Mapped[CategoriaProduto] = mapped_column(
        SAEnum(CategoriaProduto, native_enum=False, length=20), nullable=False
    )
    unidade: Mapped[UnidadeProduto] = mapped_column(
        SAEnum(UnidadeProduto, native_enum=False, length=20), nullable=False
    )
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Dispara RN02 (exige sinal_confirmado) quando true e o produto entra
    # em um pedido.
    personalizavel: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    itens_pedido: Mapped[list["ItemPedido"]] = relationship(back_populates="produto")

    def __repr__(self) -> str:
        return f"<Produto id={self.id} nome={self.nome!r}>"
