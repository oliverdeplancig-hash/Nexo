"""Login local: limite de tentativas por IP (NEXO_LIMITE_LOGIN, padrão 10/min)."""

from django.core.cache import cache


def test_limite_de_tentativas_de_login(client, db):
    cache.clear()
    for _ in range(10):
        r = client.post("/api/v1/auth/entrar/", {"usuario": "x", "senha": "y"}, content_type="application/json")
        assert r.status_code == 400
    r = client.post("/api/v1/auth/entrar/", {"usuario": "x", "senha": "y"}, content_type="application/json")
    assert r.status_code == 429
    cache.clear()
