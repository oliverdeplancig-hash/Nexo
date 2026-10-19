"""Cadastro com senha gerada, envio por e-mail e troca obrigatória (ADR-018)."""

import re
from datetime import timedelta

import pytest
from django.core import mail
from django.core.cache import cache
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.contas.credenciais import gerar_senha
from apps.contas.models import Usuario


@pytest.fixture(autouse=True)
def _limpar_limites():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def com_email(settings):
    settings.NEXO_EMAIL_HOST = "smtp.teste"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.NEXO_CREDENCIAIS = {"URL_PUBLICA": "https://nexo.teste", "VALIDADE_HORAS": 72}


def test_senha_gerada_e_forte_e_sem_caracteres_ambiguos():
    for _ in range(50):
        s = gerar_senha()
        assert len(s) == 14
        assert re.search(r"[A-Z]", s) and re.search(r"[a-z]", s) and re.search(r"\d", s) and re.search(r"[@#%+=?!]", s)
        assert not set(s) & set("0O1lI")
    assert len({gerar_senha() for _ in range(50)}) == 50


def _cadastrar(cliente_admin, **extra):
    dados = {
        "username": "novo.servidor",
        "nome_exibicao": "Novo Servidor",
        "email": "novo@exemplo.test",
        "gerar_senha": True,
    }
    dados.update(extra)
    return cliente_admin.post("/api/v1/usuarios/", dados, format="json")


def test_cadastro_gera_senha_envia_email_e_audita_sem_a_senha(cliente, usuarios, com_email):
    r = _cadastrar(cliente(usuarios["admin"]))
    assert r.status_code == 201, r.content
    cred = r.json()["credenciais"]
    assert cred["enviado_por_email"] is True and cred["destino_email"] == "novo@exemplo.test"
    senha = cred["senha_temporaria"]

    assert len(mail.outbox) == 1
    corpo = mail.outbox[0].body
    assert mail.outbox[0].to == ["novo@exemplo.test"]
    assert "Usuário: novo.servidor" in corpo and senha in corpo and "https://nexo.teste" in corpo

    u = Usuario.objects.get(username="novo.servidor")
    assert u.check_password(senha) and u.senha_temporaria and u.senha_temporaria_expira_em > timezone.now()
    eventos = EventoAuditoria.objects.filter(tipo="ADMIN_USUARIO", detalhes__acao="emitir_credenciais")
    assert eventos.count() == 1 and senha not in str(list(eventos.values()))
    # a senha só aparece na resposta do cadastro, nunca na listagem
    assert senha not in cliente(usuarios["admin"]).get("/api/v1/usuarios/").content.decode()


def test_sem_email_configurado_a_senha_aparece_para_quem_cadastrou(cliente, usuarios, settings):
    settings.NEXO_EMAIL_HOST = ""
    cred = _cadastrar(cliente(usuarios["admin"])).json()["credenciais"]
    assert cred["enviado_por_email"] is False and "não está configurado" in cred["aviso"]
    assert len(mail.outbox) == 0


def test_primeiro_acesso_exige_troca_e_bloqueia_o_resto(client, cliente, usuarios, com_email):
    senha = _cadastrar(cliente(usuarios["admin"])).json()["credenciais"]["senha_temporaria"]
    r = client.post(
        "/api/v1/auth/entrar/", {"usuario": "novo.servidor", "senha": senha}, content_type="application/json"
    )
    assert r.status_code == 200 and r.json()["trocar_senha"] is True
    assert client.get("/api/v1/documentos/").status_code == 403
    assert client.get("/api/v1/documentos/").json()["codigo"] == "trocar_senha"
    assert client.get("/api/v1/auth/eu/").status_code == 200

    trocar = lambda atual, nova: client.post(  # noqa: E731
        "/api/v1/auth/trocar-senha/", {"senha_atual": atual, "nova_senha": nova}, content_type="application/json"
    )
    assert trocar("errada", "Outra-Senha-Forte-2026").status_code == 400
    assert trocar(senha, "123").status_code == 400  # validadores de senha
    assert trocar(senha, senha).status_code == 400
    r = trocar(senha, "Minha-Senha-Nova-2026")
    assert r.status_code == 200 and r.json()["trocar_senha"] is False
    assert client.get("/api/v1/documentos/").status_code == 200  # mesma sessão continua valendo
    u = Usuario.objects.get(username="novo.servidor")
    assert u.check_password("Minha-Senha-Nova-2026") and u.senha_alterada_em is not None


def test_senha_temporaria_expirada_nao_entra(client, cliente, usuarios, com_email):
    senha = _cadastrar(cliente(usuarios["admin"])).json()["credenciais"]["senha_temporaria"]
    Usuario.objects.filter(username="novo.servidor").update(
        senha_temporaria_expira_em=timezone.now() - timedelta(minutes=1)
    )
    r = client.post(
        "/api/v1/auth/entrar/", {"usuario": "novo.servidor", "senha": senha}, content_type="application/json"
    )
    assert r.status_code == 400 and "expirou" in r.json()["detail"]


def test_gerar_nova_senha_para_quem_esqueceu(client, cliente, usuarios, com_email):
    alvo = usuarios["gp"]
    r = cliente(usuarios["admin"]).post(f"/api/v1/usuarios/{alvo.id}/gerar-senha/", format="json")
    assert r.status_code == 200
    alvo.refresh_from_db()
    assert alvo.senha_temporaria and alvo.check_password(r.json()["senha_temporaria"])
    assert not alvo.check_password("Senha-forte-123")  # a antiga deixou de valer
    assert cliente(usuarios["gp"]).post(f"/api/v1/usuarios/{alvo.id}/gerar-senha/").status_code == 403


def test_qualquer_usuario_altera_a_propria_senha(client, usuarios):
    client.post("/api/v1/auth/entrar/", {"usuario": "gp", "senha": "Senha-forte-123"}, content_type="application/json")
    r = client.post(
        "/api/v1/auth/trocar-senha/",
        {"senha_atual": "Senha-forte-123", "nova_senha": "Nova-Senha-Forte-2026"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert EventoAuditoria.objects.filter(
        tipo="ADMIN_USUARIO", usuario=usuarios["gp"], detalhes__acao="trocar_senha"
    ).exists()


def test_conta_so_microsoft_nao_troca_senha_no_nexo(cliente, usuarios):
    u = Usuario.objects.create(username="ms@pm.ba.gov.br", id_externo="oid-1")
    u.set_unusable_password()
    u.save()
    r = cliente(u).post("/api/v1/auth/trocar-senha/", {"senha_atual": "x", "nova_senha": "y"}, format="json")
    assert r.status_code == 400 and "Microsoft" in r.json()["detail"]
    assert cliente(u).get("/api/v1/auth/eu/").json()["pode_alterar_senha"] is False
