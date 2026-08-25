"""Model Usuario — autenticação (Incremento 12).

Os 3 perfis vêm das personas do CLAUDE.md, seção 4 (proprietária,
atendente, padeiro). Neste incremento todos os perfis têm o mesmo acesso —
o campo já existe e é salvo, mas nenhuma rota restringe por ele ainda
(decisão registrada: permissão diferenciada fica pra um incremento futuro,
quando houver ação que realmente precise disso).
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerfilUsuario(str, enum.Enum):
    PROPRIETARIA = "proprietaria"
    ATENDENTE = "atendente"
    PADEIRO = "padeiro"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Hash bcrypt — nunca a senha em texto puro (CLAUDE.md, seção 1.4).
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[PerfilUsuario] = mapped_column(
        SAEnum(PerfilUsuario, native_enum=False, length=20), nullable=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} email={self.email!r} perfil={self.perfil.value}>"
