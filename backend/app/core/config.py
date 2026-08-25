"""
Configuração central da aplicação.

Todas as configurações sensíveis ou dependentes de ambiente (ex.: URL do
banco) vêm de variáveis de ambiente / arquivo .env — nunca hardcoded no
código (ver CLAUDE.md, seção 1.4: "Nunca commitar segredos").
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Fallback só para quando não existe .env (ex.: clone novo, antes de
    # configurar). O banco "oficial" do projeto é PostgreSQL gerenciado via
    # Neon (decisão da seção 11 do CLAUDE.md, 2026-08-25) — configurado por
    # DATABASE_URL no .env de cada ambiente. Este default nunca deve ser
    # usado em produção.
    database_url: str = "sqlite:///./app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
