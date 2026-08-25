"""
Configuração central da aplicação.

Todas as configurações sensíveis ou dependentes de ambiente (ex.: URL do
banco) vêm de variáveis de ambiente / arquivo .env — nunca hardcoded no
código (ver CLAUDE.md, seção 1.4: "Nunca commitar segredos").
"""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Fallback só para quando não existe .env (ex.: clone novo, antes de
    # configurar). O banco "oficial" do projeto é PostgreSQL gerenciado via
    # Neon (decisão da seção 11 do CLAUDE.md, 2026-08-25) — configurado por
    # DATABASE_URL no .env de cada ambiente. Este default nunca deve ser
    # usado em produção.
    database_url: str = "sqlite:///./app.db"

    # "development" (default) ou "production" — controla só detalhes que
    # dependem de estar atrás de HTTPS de verdade (cookie de sessão, ver
    # main.py). Setar ENVIRONMENT=production no Render.
    environment: str = "development"

    # Sessão de login (Incremento 12) — cookie assinado (Starlette
    # SessionMiddleware), não JWT: mais simples e sem token pra gerenciar no
    # frontend, adequado a um único processo servindo API + UI (RNF04).
    # O default abaixo é só pra dev local nunca esquecido sem .env — em
    # produção (Render) PRECISA vir de uma variável de ambiente própria,
    # gerada por vez (ex.: `python -c "import secrets; print(secrets.token_hex(32))"`).
    session_secret_key: str = "dev-somente-troque-em-producao"
    session_max_age_horas: int = 8  # expira a sessão após um turno de trabalho

    # Bootstrap do primeiro usuário (proprietária) — só usado se o banco
    # ainda não tiver nenhum usuário cadastrado (ver app/main.py). Sem esses
    # dois, o sistema sobe sem conseguir logar ninguém — aceitável em dev
    # (ainda sem login habilitado no dia a dia local), mas precisa estar
    # setado em produção.
    admin_nome: str = "Proprietária"
    admin_email: Optional[str] = None
    admin_senha: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
