"""Teste do endpoint de verificação de saúde da API."""


def test_health_check(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
