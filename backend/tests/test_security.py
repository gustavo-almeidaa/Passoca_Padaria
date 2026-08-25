"""Testes de app/core/security.py — hash de senha (Incremento 12)."""
from app.core.security import hash_senha, verificar_senha


def test_hash_nao_guarda_senha_em_texto_puro():
    hash_resultante = hash_senha("minha-senha-secreta")

    assert hash_resultante != "minha-senha-secreta"


def test_verificar_senha_correta_retorna_true():
    hash_resultante = hash_senha("minha-senha-secreta")

    assert verificar_senha("minha-senha-secreta", hash_resultante) is True


def test_verificar_senha_errada_retorna_false():
    hash_resultante = hash_senha("minha-senha-secreta")

    assert verificar_senha("senha-errada", hash_resultante) is False


def test_verificar_senha_com_hash_invalido_nao_lanca_excecao():
    assert verificar_senha("qualquer-senha", "isso-nao-e-um-hash-bcrypt") is False
