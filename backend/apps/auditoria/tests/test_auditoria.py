import pytest
from django.db import connection, transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.servico import registrar, verificar_integridade

pytestmark = pytest.mark.django_db


def test_cadeia_integra_e_detecta_adulteracao(usuarios):
    for i in range(5):
        registrar(None, "BUSCA", usuario=usuarios["gp"], detalhes={"n": i})
    assert verificar_integridade()["integra"]

    alvo = EventoAuditoria.objects.order_by("id")[2]
    with connection.cursor() as cursor:  # simula adulteração direta, contornando o gatilho
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("ALTER TABLE auditoria_eventoauditoria DISABLE TRIGGER auditoria_bloqueia_alteracao")
        cursor.execute("UPDATE auditoria_eventoauditoria SET detalhes = '{\"n\": 99}' WHERE id = %s", [alvo.id])
        cursor.execute("ALTER TABLE auditoria_eventoauditoria ENABLE TRIGGER auditoria_bloqueia_alteracao")
    resultado = verificar_integridade()
    assert not resultado["integra"] and resultado["primeiro_evento_invalido"] == alvo.id


def test_banco_bloqueia_update_e_delete(usuarios):
    evento = registrar(None, "LOGIN", usuario=usuarios["gp"])
    with pytest.raises(Exception), transaction.atomic():
        EventoAuditoria.objects.filter(id=evento.id).update(tipo="LOGOUT")
    with pytest.raises(Exception), transaction.atomic():
        EventoAuditoria.objects.filter(id=evento.id).delete()


def test_api_exige_funcao_de_auditoria(usuarios, cliente):
    registrar(None, "LOGIN", usuario=usuarios["gp"])
    assert cliente(usuarios["gp"]).get("/api/v1/auditoria/eventos/").status_code == 403
    resposta = cliente(usuarios["auditor"]).get("/api/v1/auditoria/eventos/?tipo=LOGIN")
    assert resposta.status_code == 200 and resposta.json()["count"] >= 1
