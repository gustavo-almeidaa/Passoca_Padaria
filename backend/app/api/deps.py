"""Dependências compartilhadas de autenticação — Incremento 12.

Sessão fica guardada no cookie assinado do Starlette (`request.session`,
configurado em app/main.py) — aqui só resolve esse dado de sessão pro
Usuario correspondente, e nega acesso quando não tem sessão válida.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario

MENSAGEM_NAO_AUTENTICADO = "Sessão expirada ou inválida. Faça login novamente."


def get_usuario_atual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    usuario_id = request.session.get("usuario_id")
    if usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAGEM_NAO_AUTENTICADO
        )

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        # Usuário foi desativado/removido depois do login — sessão antiga
        # não deve continuar valendo.
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAGEM_NAO_AUTENTICADO
        )

    return usuario
