"""Comandos de instalação do servidor (ADR-019)."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.contas.models import Usuario


def test_criar_administrador_com_senha_temporaria(db, capsys):
    call_command("criar_administrador", usuario="chefe", nome="Chefe", email="")
    u = Usuario.objects.get(username="chefe")
    saida = capsys.readouterr().out
    senha = saida.split("Senha temporária (aparece só agora): ")[1].split()[0]
    assert u.check_password(senha) and u.senha_temporaria
    assert {"admin_permissoes", "admin_usuarios", "ver_auditoria", "importar_documentos"} <= u.funcoes()
    with pytest.raises(CommandError, match="já existe"):
        call_command("criar_administrador", usuario="chefe")


def test_preparar_producao_recusa_debug_e_desativa_demo(db, settings, usuarios):
    settings.DEBUG = True
    with pytest.raises(CommandError, match="NEXO_DEBUG"):
        call_command("preparar_producao")
    settings.DEBUG = False
    settings.SECRET_KEY = "x" * 50
    demo = Usuario.objects.create_user(username="admin.demo", password="Nexo@demo2026")
    call_command("preparar_producao")
    demo.refresh_from_db()
    assert demo.is_active is False


def test_gerar_certificado(tmp_path):
    from cryptography import x509

    call_command("gerar_certificado", pasta=str(tmp_path), nome=["nexo.unidade.local"], ip=["10.1.2.3"])
    cert = x509.load_pem_x509_certificate((tmp_path / "nexo.crt").read_bytes())
    alt = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "nexo.unidade.local" in alt.get_values_for_type(x509.DNSName)
    assert "10.1.2.3" in [str(i) for i in alt.get_values_for_type(x509.IPAddress)]
    assert (tmp_path / "nexo.key").exists() and (tmp_path / "nexo.cer").exists()
