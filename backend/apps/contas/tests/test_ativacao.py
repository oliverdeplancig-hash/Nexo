"""Link de ativação: a pessoa cria a própria senha (ADR-027)."""

import re

import pytest
from django.core import mail
from django.core.cache import cache

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario

pytestmark = pytest.mark.django_db
ATIVAR = "/api/v1/auth/ativar-conta/"


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


def _link():
    return re.search(r"/ativar-conta\?u=([\w-]+)&t=([\w-]+)", mail.outbox[-1].body).groups()


def test_cadastro_com_link_e_ativacao(cliente, usuarios, com_email):
    admin = cliente(usuarios["admin"])
    r = admin.post(
        "/api/v1/usuarios/",
        {"username": "nova.pessoa", "email": "nova@instituicao.teste", "enviar_link": True},
        format="json",
    )
    assert r.status_code == 201 and r.json()["link"]["enviado_por_email"]
    assert "credenciais" not in r.json()  # nenhuma senha volta para quem cadastrou
    pessoa = Usuario.objects.get(username="nova.pessoa")
    assert not pessoa.has_usable_password()
    corpo = mail.outbox[-1].body
    assert (
        "https://nexo.teste/ativar-conta?u=" in corpo
        and "senha" not in corpo.split("Usuário:")[1].lower().split("o link")[0]
    )

    u, t = _link()
    publico = cliente()
    assert publico.post(ATIVAR, {"u": u, "t": t}, format="json").json()["usuario"] == "nova.pessoa"
    assert publico.post(ATIVAR, {"u": u, "t": t, "nova_senha": "curta"}, format="json").status_code == 400
    assert publico.post(ATIVAR, {"u": u, "t": t, "nova_senha": "Minha-senha-forte-7"}, format="json").status_code == 200
    pessoa.refresh_from_db()
    assert pessoa.check_password("Minha-senha-forte-7") and not pessoa.senha_temporaria
    assert publico.post(ATIVAR, {"u": u, "t": t, "nova_senha": "Outra-senha-forte-8"}, format="json").status_code == 400
    acoes = set(EventoAuditoria.objects.values_list("detalhes__acao", flat=True))
    assert {"enviar_link_ativacao", "ativar_conta"} <= acoes


def test_link_expira_e_reenvio_invalida_o_anterior(cliente, usuarios, com_email, settings):
    admin = cliente(usuarios["admin"])
    usuarios["gp"].email = "gp@instituicao.teste"
    usuarios["gp"].save()
    admin.post(f"/api/v1/usuarios/{usuarios['gp'].id}/enviar-link/")
    primeiro = _link()
    admin.post(f"/api/v1/usuarios/{usuarios['gp'].id}/enviar-link/")
    segundo = _link()
    publico = cliente()
    assert publico.post(ATIVAR, dict(zip("ut", primeiro, strict=True)), format="json").status_code == 400
    settings.NEXO_ATIVACAO_HORAS = -1
    assert publico.post(ATIVAR, dict(zip("ut", segundo, strict=True)), format="json").status_code == 400  # expirado
    settings.NEXO_ATIVACAO_HORAS = 72
    assert publico.post(ATIVAR, dict(zip("ut", segundo, strict=True)), format="json").status_code == 200


def test_sem_email_configurado_nao_oferece_link(cliente, usuarios):
    r = cliente(usuarios["admin"]).post(
        "/api/v1/usuarios/", {"username": "x.y", "email": "x@y.teste", "enviar_link": True}, format="json"
    )
    assert r.status_code == 400 and not Usuario.objects.filter(username="x.y").exists()
    assert cliente().get("/api/v1/auth/provedores/").json()["link_por_email"] is False


def test_nao_mistura_formas_de_acesso(cliente, usuarios, com_email):
    r = cliente(usuarios["admin"]).post(
        "/api/v1/usuarios/",
        {"username": "a.b", "email": "a@b.teste", "enviar_link": True, "gerar_senha": True},
        format="json",
    )
    assert r.status_code == 400
