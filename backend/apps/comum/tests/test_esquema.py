"""Especificação OpenAPI (ADR-026)."""

import pytest

pytestmark = pytest.mark.django_db


def test_esquema_so_para_ti(cliente, usuarios):
    assert cliente().get("/api/v1/esquema/").status_code == 403
    assert cliente(usuarios["gp"]).get("/api/v1/esquema/").status_code == 403
    r = cliente(usuarios["auditor"]).get("/api/v1/esquema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert r.status_code == 200
    esquema = r.json()
    assert esquema["info"]["title"] == "Nexo — API"
    assert "/api/v1/documentos/" in esquema["paths"]
    assert "/api/v1/auth/esqueci-senha/" in esquema["paths"]  # rota de função aparece com corpo livre


def test_documentacao_navegavel_sem_cdn(cliente, usuarios):
    r = cliente(usuarios["auditor"]).get("/api/v1/documentacao/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "swagger-ui" in html and "cdn.jsdelivr" not in html and "unpkg" not in html
