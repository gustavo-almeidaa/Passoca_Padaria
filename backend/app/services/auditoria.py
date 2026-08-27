"""Trilha de auditoria de operações sensíveis — Incremento 18 (achado A-01).

`registrar_evento` só **adiciona** o evento à sessão; quem chama é
responsável pelo `commit` — assim o registro entra na mesma transação da
operação de negócio e não existe mudança de estado sem rastro.

Cobre (recomendação da auditoria: "toda operação que altere estado de
pedido, preço de produto ou cadastro de usuário"):
- pedido: criar, avançar status, confirmar sinal, cancelar
- produto: criar, editar
- usuário: criar, desativar, trocar senha (nunca grava o valor da senha)
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.evento_auditoria import EventoAuditoria
from app.models.usuario import Usuario

ENTIDADE_PEDIDO = "pedido"
ENTIDADE_PRODUTO = "produto"
ENTIDADE_USUARIO = "usuario"


def registrar_evento(
    db: Session,
    *,
    usuario: Usuario,
    entidade: str,
    entidade_id: int,
    acao: str,
    anterior: dict[str, Any] | None = None,
    posterior: dict[str, Any] | None = None,
) -> None:
    db.add(
        EventoAuditoria(
            usuario_id=usuario.id,
            usuario_email=usuario.email,
            usuario_perfil=usuario.perfil.value,
            entidade=entidade,
            entidade_id=entidade_id,
            acao=acao,
            estado_anterior=anterior,
            estado_posterior=posterior,
        )
    )


def _valor(campo: Any) -> Any:
    """Normaliza enums (-> .value) e Decimal (-> str) para caber em JSON."""
    if hasattr(campo, "value"):
        return campo.value
    if campo.__class__.__name__ == "Decimal":
        return str(campo)
    return campo


def snapshot_pedido(pedido: Any) -> dict[str, Any]:
    return {
        "status": _valor(pedido.status),
        "sinal_confirmado": pedido.sinal_confirmado,
    }


def snapshot_produto(produto: Any) -> dict[str, Any]:
    return {
        "nome": produto.nome,
        "categoria": _valor(produto.categoria),
        "unidade": _valor(produto.unidade),
        "preco": _valor(produto.preco),
        "personalizavel": produto.personalizavel,
        "ativo": produto.ativo,
    }
