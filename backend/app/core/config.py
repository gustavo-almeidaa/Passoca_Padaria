"""
Configuração central da aplicação.

Todas as configurações sensíveis ou dependentes de ambiente (ex.: URL do
banco) vêm de variáveis de ambiente / arquivo .env — nunca hardcoded no
código (ver CLAUDE.md, seção 1.4: "Nunca commitar segredos").
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # SQLite por padrão para desenvolvimento local (decisão da seção 11 do
    # CLAUDE.md). O caminho é relativo ao diretório de onde o processo roda.
    database_url: str = "sqlite:///./app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
