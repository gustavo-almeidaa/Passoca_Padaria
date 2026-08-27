"""Dependências compartilhadas de autenticação — Incremento 12.

Sessão fica guardada no cookie assinado do Starlette (`request.session`,
configurado em app/main.py) — aqui só resolve esse dado de sessão pro
Usuario correspondente, e nega acesso quando não tem sessão válida.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import PerfilUsuario, Usuario

MENSAGEM_NAO_AUTENTICADO = "Sessão expirada ou inválida. Faça login novamente."
MENSAGEM_SO_PROPRIETARIA = (
    "Só a proprietária pode gerenciar usuários (decisão registrada em "
    "CLAUDE.md, seção 11 — 2026-08-25, pra evitar erro ou troca indesejada)."
)


def obter_ip_cliente(request: Request) -> str:
    """IP de origem da requisição — usado pelo limite de tentativas de login
    (Incremento 17).

    Atrás do proxy do Render, `request.client.host` é o proxy, não o
    cliente; o IP real vem como 1ª entrada do `X-Forwarded-For`. Em dev
    local (sem proxy) o header não existe e caímos no `request.client`.
    Forjar o header em dev é inofensivo (não há atacante); em produção o
    Render controla esse header.
    """
    encaminhado = request.headers.get("x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "desconhecido"


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


def exigir_proprietaria(usuario_atual: Usuario = Depends(get_usuario_atual)) -> Usuario:
    """Gate de perfil (Incremento 15) — primeira e única restrição por
    perfil que existe até agora (as outras rotas continuam iguais pra
    qualquer usuário autenticado, ver CLAUDE.md seção 11)."""
    if usuario_atual.perfil != PerfilUsuario.PROPRIETARIA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=MENSAGEM_SO_PROPRIETARIA
        )
    return usuario_atual
