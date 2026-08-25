"""
Ponto de entrada da API — Padaria do Passoca.

Autenticação por sessão desde o Incremento 12 (CLAUDE.md, seção 11, decisão
de 2026-08-25) — necessária porque o deploy em PaaS público (Render) expõe
o sistema na internet, diferente do cenário original "só rede interna".
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, clientes, pedidos, produtos
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_senha
from app.models.usuario import PerfilUsuario, Usuario

# backend/app/main.py -> sobe 3 níveis até a raiz do repo, onde fica /frontend.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

logger = logging.getLogger("passoca")

DEV_SESSION_SECRET_KEY = "dev-somente-troque-em-producao"


def _validar_configuracao_producao() -> None:
    """Recusa subir em produção com a secret key de dev — nesse caso
    qualquer um que leia o código-fonte consegue forjar sessão de login
    (CLAUDE.md, seção 1.4: segurança nunca é opcional por prazo)."""
    if (
        settings.environment == "production"
        and settings.session_secret_key == DEV_SESSION_SECRET_KEY
    ):
        raise RuntimeError(
            "ENVIRONMENT=production mas SESSION_SECRET_KEY ainda é o valor "
            "de desenvolvimento. Configure uma chave própria (ex.: "
            '`python -c "import secrets; print(secrets.token_hex(32))"`) '
            "antes de subir em produção."
        )


def _bootstrap_usuario_inicial() -> None:
    """Cria a conta da proprietária no primeiro start, se ainda não existir
    nenhum usuário — só assim dá pra logar pela primeira vez (Incremento 12).
    Não faz nada se o banco já tem usuário, ou se ADMIN_EMAIL/ADMIN_SENHA
    não estiverem configurados (dev local sem login habilitado ainda).
    """
    db = SessionLocal()
    try:
        if db.query(Usuario).first() is not None:
            return
        if not settings.admin_email or not settings.admin_senha:
            logger.warning(
                "Nenhum usuário cadastrado e ADMIN_EMAIL/ADMIN_SENHA não "
                "configurados — login ficará indisponível até isso ser "
                "definido no ambiente."
            )
            return

        usuario = Usuario(
            nome=settings.admin_nome,
            email=settings.admin_email,
            senha_hash=hash_senha(settings.admin_senha),
            perfil=PerfilUsuario.PROPRIETARIA,
        )
        db.add(usuario)
        db.commit()
        logger.info("Usuário inicial criado: %s", settings.admin_email)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validar_configuracao_producao()
    _bootstrap_usuario_inicial()
    yield


app = FastAPI(
    title="Padaria do Passoca — API",
    description=(
        "API interna para cadastro de clientes, produtos e ciclo de vida de "
        "pedidos (RF01-RF07)."
    ),
    version="0.5.0",
    lifespan=lifespan,
)

# Cookie de sessão assinado (não JWT — ver core/config.py). `https_only`
# fica ligado fora de dev pra o cookie nunca trafegar sem TLS.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    max_age=settings.session_max_age_horas * 3600,
    same_site="lax",
    https_only=settings.environment == "production",
)

app.include_router(auth.router)
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
