"""Model TentativaLogin — Incremento 17 (auditoria A-02).

Registra cada tentativa de login (com ou sem sucesso) para alimentar o
limite de tentativas por IP em `app/services/rate_limit.py`. As falhas
registradas aqui vão ser religadas à trilha de auditoria de negócio no A-01.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TentativaLogin(Base):
    __tablename__ = "tentativas_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    # E-mail informado na tentativa (normalizado para minúsculas). Pode não
    # corresponder a nenhum usuário — registrar mesmo assim ajuda a
    # identificar varredura de e-mails.
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # IP de origem. String(45) cabe um IPv6 completo.
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    sucesso: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Escrito explicitamente pela aplicação (não pelo server_default) para o
    # cálculo da janela usar o mesmo relógio da inserção — o server_default
    # fica só como rede de segurança.
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # A consulta do rate limit filtra por ip + criado_em na janela.
        Index("ix_tentativas_login_ip_criado_em", "ip", "criado_em"),
    )

    def __repr__(self) -> str:
        return (
            f"<TentativaLogin ip={self.ip!r} email={self.email!r} "
            f"sucesso={self.sucesso}>"
        )
