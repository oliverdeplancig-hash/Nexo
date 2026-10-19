"""Servidor de rede Windows (ADR-019): HTTPS e telas servidas pelo backend."""

from django.test import override_settings


@override_settings(NEXO_REDIRECIONAR_HTTPS=True, NEXO_PORTA_HTTPS=8443, ALLOWED_HOSTS=["nexo-pc", "testserver"])
def test_http_redireciona_para_a_porta_https(client, db):
    r = client.get("/colecoes?x=1", HTTP_HOST="nexo-pc:8080")
    assert r.status_code == 301 and r["Location"] == "https://nexo-pc:8443/colecoes?x=1"
    assert client.get("/api/v1/saude/", HTTP_HOST="nexo-pc:8080").status_code == 200  # monitoramento em HTTP


@override_settings(NEXO_REDIRECIONAR_HTTPS=True, NEXO_PORTA_HTTPS=443, ALLOWED_HOSTS=["nexo-pc"])
def test_porta_padrao_nao_aparece(client, db):
    assert client.get("/", HTTP_HOST="nexo-pc")["Location"] == "https://nexo-pc/"


@override_settings(NEXO_REDIRECIONAR_HTTPS=True, ALLOWED_HOSTS=["nexo-pc"])
def test_https_nao_redireciona(client, db):
    assert client.get("/api/v1/saude/", HTTP_HOST="nexo-pc", secure=True).status_code == 200


def test_aplicativo_devolve_index_ou_aviso(rf, settings, tmp_path):
    from apps.comum.views import aplicativo

    settings.NEXO_FRONTEND_DIST = tmp_path
    assert aplicativo(rf.get("/colecoes")).status_code == 503
    (tmp_path / "index.html").write_text("<!doctype html><title>Nexo</title>")
    r = aplicativo(rf.get("/colecoes"))
    assert r.status_code == 200 and r["Cache-Control"] == "no-cache"
    assert b"<title>Nexo</title>" in b"".join(r.streaming_content)
