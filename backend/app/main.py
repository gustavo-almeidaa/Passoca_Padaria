"""
Ponto de entrada da API — Padaria do Passoca.

Sem autenticação (decisão registrada em CLAUDE.md, seção 11): o sistema roda
hoje na rede interna da padaria. Ver CLAUDE.md, seção 4, nota de 2026-08-24,
para a ressalva sobre expor isso à internet no futuro.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import clientes, pedidos, produtos

# backend/app/main.py -> sobe 3 níveis até a raiz do repo, onde fica /frontend.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

logger = logging.getLogger("passoca")

app = FastAPI(
    title="Padaria do Passoca — API",
    description=(
        "API interna para cadastro de clientes, produtos e ciclo de vida de "
        "pedidos (RF01-RF07)."
    ),
    version="0.4.0",
)

app.include_router(clientes.router)
app.include_router(produtos.router)
app.include_router(pedidos.router)


@app.get("/health", tags=["infra"])
def health_check() -> dict[str, str]:
    """Verificação simples de que a API está no ar."""
    return {"status": "ok"}


# Frontend estático (HTML/CSS/JS puro, CLAUDE.md seção 11) servido pelo
# mesmo processo da API — sem CORS a configurar, um único comando
# (`uvicorn app.main:app`) sobe o sistema inteiro (RNF04). Montado por
# último: rotas de API declaradas acima continuam tendo prioridade sobre
# este catch-all de arquivos estáticos.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logger.warning(
        "Diretório de frontend não encontrado em %s — servindo só a API.",
        FRONTEND_DIR,
    )


@app.exception_handler(Exception)
async def erro_interno_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Rede de segurança para qualquer erro não tratado explicitamente.

    Loga o detalhe completo internamente (stack trace incluído) e devolve
    ao cliente só uma mensagem genérica — nunca stack trace, nome de
    tabela/coluna, ou qualquer detalhe interno (CLAUDE.md, seção 1.4).
    """
    logger.exception(
        "Erro não tratado ao processar %s %s", request.method, request.url
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Tente novamente em instantes."},
    )
