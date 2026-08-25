"""Schemas Pydantic de Usuario — autenticação (Incremento 12)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.usuario import PerfilUsuario


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: PerfilUsuario

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o nome do usuário.")
        return v

    @field_validator("senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha precisa ter pelo menos 8 caracteres.")
        return v


class TrocarSenhaRequest(BaseModel):
    """RF novo (Incremento 14): usuário logado troca a própria senha —
    exige a senha atual pra confirmar que é mesmo o dono da conta."""

    senha_atual: str
    senha_nova: str

    @field_validator("senha_nova")
    @classmethod
    def senha_nova_minima(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A nova senha precisa ter pelo menos 8 caracteres.")
        return v


class UsuarioRead(BaseModel):
    """Nunca inclui senha_hash — o que sai da API não expõe o hash da senha."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    perfil: PerfilUsuario
    ativo: bool
    criado_em: datetime
