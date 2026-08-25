"""
Hash de senha — Incremento 12.

bcrypt direto (sem passlib): a lib passlib está sem manutenção ativa e tem
tido atrito de compatibilidade com versões recentes do bcrypt. O uso aqui é
simples o bastante (hash + verify) pra não precisar da camada extra
(CLAUDE.md, seção 1.4: senha sempre com hash forte, nunca texto puro).
"""
from __future__ import annotations

import bcrypt


def hash_senha(senha_texto_puro: str) -> str:
    hash_bytes = bcrypt.hashpw(senha_texto_puro.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_senha(senha_texto_puro: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha_texto_puro.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        # senha_hash corrompido/formato inesperado — trata como senha errada,
        # nunca deixa vazar detalhe interno pro chamador.
        return False
