"""Teste do endpoint de verificação de saúde da API."""
import re


def test_health_check(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_toda_resposta_tem_header_de_tempo(client):
    """Incremento 22 (A-07): o middleware de instrumentação carimba
    `X-Response-Time` em toda resposta."""
    resp = client.get("/health")

    assert re.fullmatch(r"\d+ms", resp.headers.get("x-response-time", ""))


def test_rota_login_serve_a_pagina_de_login(client_anonimo):
    """Incremento 25: `/login` é página própria, não exige sessão."""
    resp = client_anonimo.get("/login")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert 'id="form-login"' in resp.text
