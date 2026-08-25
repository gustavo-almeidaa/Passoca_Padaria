"""Schemas Pydantic de Cliente — RF01 (cadastrar cliente)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ClienteBase(BaseModel):
    nome: str
    telefone: str
    # Opcional — nem todo cliente recebe entrega (ver app/models/cliente.py).
    endereco: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o nome do cliente.")
        return v

    @field_validator("telefone")
    @classmethod
    def telefone_valido(cls, v: str) -> str:
        v = v.strip()
        digitos = "".join(c for c in v if c.isdigit())
        if len(digitos) < 8:
            raise ValueError("Informe um telefone válido, com DDD.")
        return v

    @field_validator("endereco")
    @classmethod
    def endereco_vazio_vira_none(cls, v: Optional[str]) -> Optional[str]:
        # Normaliza "" / só espaços pra None, em vez de guardar string vazia
        # no banco — evita distinguir "" de "nunca preencheu" sem necessidade.
        if v is None:
            return None
        v = v.strip()
        return v or None


class ClienteCreate(ClienteBase):
    pass


class ClienteRead(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
