"""Limite de tentativas de login por IP — Incremento 17 (auditoria A-02).

Estratégia (decisão do usuário, 2026-08-27): **a conta nunca trava — só o
IP de origem**. Assim um ataque remoto de força bruta / credential stuffing
não consegue deixar a proprietária (única com gestão de usuários) trancada
para fora do sistema.

Contagem de falhas por IP numa janela rolante de 15 min:

- até 4 falhas: login normal.
- de 5 a 9 falhas: atraso progressivo antes de responder (0,5s dobrando
  até o teto de 5s).
- 10 falhas ou mais: 429 imediato, sem checar a senha, com Retry-After.

Janela rolante: as falhas "saem" sozinhas depois de 15 min, sem
desbloqueio manual. `agora` é injetável (mesmo padrão de
`services/pedidos.py`) para testes determinísticos da janela.

Limitação conhecida (registrada no relatório do Incremento 17): o atraso
usa `time.sleep` numa thread do pool (o código é síncrono). Um atacante na
faixa de 5 a 9 falhas segura algumas threads por até 5s — DoS leve,
mitigado pelo 429 imediato (sem sleep) a partir de 10 falhas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.tentativa_login import TentativaLogin

# Janela rolante considerada para a contagem de falhas.
JANELA = timedelta(minutes=15)
# A partir desta contagem de falhas na janela, aplica atraso progressivo.
LIMIAR_ATRASO = 5
# A partir desta contagem, bloqueia com 429 sem nem verificar a senha.
LIMIAR_BLOQUEIO = 10
ATRASO_BASE_SEGUNDOS = 0.5
ATRASO_MAX_SEGUNDOS = 5.0
# Tentativas mais antigas que isto são apagadas a cada escrita (poda barata).
RETENCAO = timedelta(days=7)


@dataclass
class ResultadoRateLimit:
    """O que a camada de API deve fazer antes de processar o login."""

    bloqueado: bool = False
    retry_after_segundos: int = 0
    atraso_segundos: float = 0.0


def avaliar_ip(
    db: Session, ip: str, *, agora: datetime | None = None
) -> ResultadoRateLimit:
    """Decide se este IP deve ser bloqueado, atrasado ou liberado, com base
    nas falhas de login dele na janela."""
    agora = agora or datetime.now()
    inicio_janela = agora - JANELA

    momentos_de_falha = [
        criado_em
        for (criado_em,) in (
            db.query(TentativaLogin.criado_em)
            .filter(
                TentativaLogin.ip == ip,
                TentativaLogin.sucesso.is_(False),
                TentativaLogin.criado_em >= inicio_janela,
            )
            .order_by(TentativaLogin.criado_em.desc())
            .all()
        )
    ]
    falhas = len(momentos_de_falha)

    if falhas >= LIMIAR_BLOQUEIO:
        # Destrava quando a LIMIAR_BLOQUEIO-ésima falha mais recente sair da
        # janela (aí a contagem cai para LIMIAR_BLOQUEIO - 1).
        libera_em = momentos_de_falha[LIMIAR_BLOQUEIO - 1] + JANELA
        retry_after = max(1, math.ceil((libera_em - agora).total_seconds()))
        return ResultadoRateLimit(
            bloqueado=True, retry_after_segundos=retry_after
        )

    if falhas >= LIMIAR_ATRASO:
        atraso = min(
            ATRASO_BASE_SEGUNDOS * 2 ** (falhas - LIMIAR_ATRASO),
            ATRASO_MAX_SEGUNDOS,
        )
        return ResultadoRateLimit(atraso_segundos=atraso)

    return ResultadoRateLimit()


def registrar_tentativa(
    db: Session,
    *,
    email: str,
    ip: str,
    sucesso: bool,
    agora: datetime | None = None,
) -> None:
    """Grava a tentativa e poda as antigas. Commita."""
    agora = agora or datetime.now()
    db.add(
        TentativaLogin(
            email=email.strip().lower()[:255],
            ip=ip,
            sucesso=sucesso,
            criado_em=agora,
        )
    )
    db.query(TentativaLogin).filter(
        TentativaLogin.criado_em < agora - RETENCAO
    ).delete(synchronize_session=False)
    db.commit()
