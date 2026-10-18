from __future__ import annotations

import logging

from django.db import connection, transaction
from django.utils import timezone

from .models import EventoAuditoria

logger = logging.getLogger("nexo.auditoria")

# Chave do advisory lock que serializa a gravação da cadeia de hashes.
_TRAVA_CADEIA = 7_310_001


def _ip(request) -> str | None:
    if request is None:
        return None
    meta = getattr(request, "META", None)
    if meta is None:  # scope de WebSocket
        cliente = getattr(request, "get", lambda *_: None)("client")
        return cliente[0] if cliente else None
    # Atrás de proxy reverso confiável, configure o proxy para sobrescrever
    # X-Forwarded-For; aqui usamos REMOTE_ADDR para não confiar em cabeçalho do cliente.
    return meta.get("REMOTE_ADDR")


def registrar(
    request=None,
    tipo: str = "",
    *,
    usuario=None,
    objeto=None,
    resultado: str = "SUCESSO",
    detalhes: dict | None = None,
    ip: str | None = None,
) -> EventoAuditoria | None:
    """Grava um evento na trilha. Falhas de auditoria são registradas em log
    e propagadas: uma operação auditável não deve seguir sem trilha."""
    if usuario is None and request is not None:
        candidato = getattr(request, "user", None)
        if candidato is None and isinstance(request, dict):
            candidato = request.get("user")
        if candidato is not None and getattr(candidato, "is_authenticated", False):
            usuario = candidato

    evento = EventoAuditoria(
        tipo=tipo,
        resultado=resultado,
        usuario=usuario,
        usuario_login=getattr(usuario, "username", "") or "",
        setor_sigla=(usuario.setor.sigla if usuario is not None and getattr(usuario, "setor_id", None) else ""),
        objeto_tipo=objeto.__class__.__name__ if objeto is not None else "",
        objeto_id=str(getattr(objeto, "pk", "") or "") if objeto is not None else "",
        objeto_descricao=str(objeto)[:300] if objeto is not None else "",
        ip=ip or _ip(request),
        detalhes=detalhes or {},
    )
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_TRAVA_CADEIA])
        ultimo = EventoAuditoria.objects.order_by("-id").values_list("hash", flat=True).first()
        evento.hash_anterior = ultimo or ""
        evento.ocorrido_em = timezone.now()
        evento.hash = evento.calcular_hash()
        evento.save()
    return evento


def verificar_integridade(limite: int | None = None) -> dict:
    """Recalcula a cadeia do início ao fim e aponta o primeiro elo quebrado."""
    anterior = ""
    total = 0
    qs = EventoAuditoria.objects.order_by("id")
    if limite:
        qs = qs[:limite]
    for evento in qs.iterator():
        total += 1
        if evento.hash_anterior != anterior or evento.calcular_hash() != evento.hash:
            return {"integra": False, "eventos_verificados": total, "primeiro_evento_invalido": evento.id}
        anterior = evento.hash
    return {"integra": True, "eventos_verificados": total, "primeiro_evento_invalido": None}
