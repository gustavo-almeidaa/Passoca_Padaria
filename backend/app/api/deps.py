"""Dependências compartilhadas de autenticação — Incremento 12.

Sessão fica guardada no cookie assinado do Starlette (`request.session`,
configurado em app/main.py) — aqui só resolve esse dado de sessão pro
Usuario correspondente, e nega acesso quando não tem sessão válida.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import PerfilUsuario, Usuario

MENSAGEM_NAO_AUTENTICADO = "Sessão expirada ou inválida. Faça login novamente."
MENSAGEM_SO_PROPRIETARIA = (
    "Esta área é restrita à proprietária. Se precisar de acesso, fale com ela."
)

_ROTULO_PERFIL = {
    PerfilUsuario.PROPRIETARIA: "proprietária",
    PerfilUsuario.ATENDENTE: "atendente",
    PerfilUsuario.PADEIRO: "padeiro(a)",
}

# Incremento 19 (auditoria A-03): operações de balcão que mudam dados
# (cadastrar cliente, mexer em produto, registrar/confirmar/cancelar
# pedido) são da proprietária e do atendente. O padeiro tem acesso de
# leitura + avançar status de produção — nada além disso.
PERFIS_BALCAO = (PerfilUsuario.PROPRIETARIA, PerfilUsuario.ATENDENTE)


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
    """Gate exclusivo da proprietária (Incremento 15) — aba Usuários e
    trilha de auditoria. Mensagem própria porque referencia a decisão
    registrada no CLAUDE.md."""
    if usuario_atual.perfil != PerfilUsuario.PROPRIETARIA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=MENSAGEM_SO_PROPRIETARIA
        )
    return usuario_atual


def exigir_perfis(
    *perfis: PerfilUsuario, acao: str = "fazer isso"
) -> Callable[..., Usuario]:
    """Fábrica de dependência de perfil (Incremento 19, auditoria A-03).

    Uso: `Depends(exigir_perfis(*PERFIS_BALCAO, acao="cancelar pedidos"))`.
    Retorna o próprio usuário logado, então serve tanto como gate em
    `dependencies=[...]` quanto como parâmetro injetado (ex.: nas rotas que
    também gravam a trilha de auditoria).
    """
    permitidos = set(perfis)

    def _checar(usuario_atual: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario_atual.perfil not in permitidos:
            quem = ", ".join(_ROTULO_PERFIL[p] for p in perfis)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Seu perfil ({_ROTULO_PERFIL[usuario_atual.perfil]}) não "
                    f"pode {acao}. Permitido para: {quem}."
                ),
            )
        return usuario_atual

    return _checar
