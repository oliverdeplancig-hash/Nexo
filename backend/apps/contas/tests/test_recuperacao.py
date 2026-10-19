"""Recuperação de senha pelo próprio usuário (ADR-024)."""

import re

import pytest
from django.core import mail
from django.core.cache import cache

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario

pytestmark = pytest.mark.django_db
ESQUECI = "/api/v1/auth/esqueci-senha/"
REDEFINIR = "/api/v1/auth/redefinir-senha/"


@pytest.fixture(autouse=True)
def _limpo():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def com_email(settings):
    settings.NEXO_EMAIL_HOST = "smtp.teste"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.NEXO_CREDENCIAIS = {"URL_PUBLICA": "https://nexo.teste", "VALIDADE_HORAS": 72}
    settings.NEXO_RECUPERACAO = {**settings.NEXO_RECUPERACAO, "ENVIO_EM_SEGUNDO_PLANO": False}


@pytest.fixture
def pessoa(usuarios):
    u = usuarios["gp"]
    u.email = "gp@instituicao.teste"
    u.save()
    return u


def _link(cliente):
    corpo = mail.outbox[-1].body
    u, t = re.search(r"/redefinir-senha\?u=([\w-]+)&t=([\w-]+)", corpo).groups()
    return u, t


def test_resposta_igual_com_ou_sem_conta(cliente, com_email, pessoa):
    c = cliente()
    existe = c.post(ESQUECI, {"identificacao": "gp@instituicao.teste"}, format="json")
    nao_existe = c.post(ESQUECI, {"identificacao": "ninguem@instituicao.teste"}, format="json")
    assert existe.status_code == nao_existe.status_code == 200
    assert existe.json() == nao_existe.json()
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["gp@instituicao.teste"]
    assert "https://nexo.teste/redefinir-senha?u=" in mail.outbox[0].body


def test_link_cria_nova_senha_uma_vez_so(cliente, com_email, pessoa):
    c = cliente()
    c.post(ESQUECI, {"identificacao": "gp"}, format="json")
    u, t = _link(c)
    assert c.post(REDEFINIR, {"u": u, "t": t}, format="json").json()["usuario"] == "gp"
    fraca = c.post(REDEFINIR, {"u": u, "t": t, "nova_senha": "123"}, format="json")
    assert fraca.status_code == 400 and fraca.json()["nova_senha"]
    ok = c.post(REDEFINIR, {"u": u, "t": t, "nova_senha": "Outra-senha-forte-9"}, format="json")
    assert ok.status_code == 200
    pessoa.refresh_from_db()
    assert pessoa.check_password("Outra-senha-forte-9") and not pessoa.senha_temporaria
    assert "foi alterada" in mail.outbox[-1].subject
    de_novo = c.post(REDEFINIR, {"u": u, "t": t, "nova_senha": "Mais-uma-senha-forte-1"}, format="json")
    assert de_novo.status_code == 400  # uso único
    acoes = list(EventoAuditoria.objects.filter(tipo="ADMIN_USUARIO").values_list("detalhes__acao", flat=True))
    assert "pedir_recuperacao" in acoes and "recuperar_senha" in acoes
    assert "Outra-senha-forte-9" not in str(list(EventoAuditoria.objects.values_list("detalhes", flat=True)))


def test_link_expirado_ou_adulterado(cliente, com_email, pessoa, settings):
    c = cliente()
    c.post(ESQUECI, {"identificacao": "gp"}, format="json")
    u, t = _link(c)
    assert c.post(REDEFINIR, {"u": u, "t": t[:-2] + "xx"}, format="json").status_code == 400
    settings.PASSWORD_RESET_TIMEOUT = -1
    assert c.post(REDEFINIR, {"u": u, "t": t}, format="json").status_code == 400


def test_contas_que_nao_recuperam(cliente, com_email, usuarios):
    microsoft = Usuario.objects.create_user(username="ms", email="ms@instituicao.teste")
    microsoft.set_unusable_password()
    microsoft.save()
    inativa = Usuario.objects.create_user(
        username="ina", email="ina@instituicao.teste", password="x" * 12, is_active=False
    )
    c = cliente()
    for ident in ("ms", inativa.username):
        assert c.post(ESQUECI, {"identificacao": ident}, format="json").status_code == 200
    assert mail.outbox == []


def test_limite_por_conta_e_desligado_sem_email(cliente, com_email, pessoa, settings):
    c = cliente()
    for _ in range(5):
        c.post(ESQUECI, {"identificacao": "gp"}, format="json")
    assert len(mail.outbox) == 3  # no máximo 3 e-mails por hora por conta
    settings.NEXO_EMAIL_HOST = ""
    cache.clear()
    assert c.post(ESQUECI, {"identificacao": "gp"}, format="json").status_code == 400
    assert cliente().get("/api/v1/auth/provedores/").json()["recuperar_senha"] is False


def test_limite_por_endereco(cliente, com_email, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "recuperacao": "2/hour"},
    }
    from rest_framework.throttling import SimpleRateThrottle

    SimpleRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    try:
        c = cliente()
        codigos = [c.post(ESQUECI, {"identificacao": "x"}, format="json").status_code for _ in range(3)]
        assert codigos == [200, 200, 429]
    finally:
        from rest_framework.settings import api_settings

        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
