from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.comum.permissoes import exige_funcao
from apps.contas.models import Funcao

from . import copia


@api_view(["GET"])
@permission_classes([exige_funcao(Funcao.ADMIN_PERMISSOES)])
def situacao_copias(request):
    """Painel do administrador: as cópias estão em dia? Criar e restaurar são feitos no servidor (comando)."""
    cfg = settings.NEXO_BACKUP
    copias = copia.listar()
    agendadas = [c for c in copias if c.get("rotulo", "nexo") == copia.ROTULO_AGENDADA and c.get("criada_em")]
    ultima = agendadas[0] if agendadas else None
    horas = None
    if ultima:
        horas = round((timezone.now() - datetime.fromisoformat(ultima["criada_em"])).total_seconds() / 3600, 1)
    return Response(
        {
            "pasta": str(cfg["DIR"]),
            "senha_configurada": bool(cfg["SENHA"]),
            "retencao": cfg["RETENCAO"],
            "alerta_horas": cfg["ALERTA_HORAS"],
            "horas_desde_ultima": horas,
            "em_dia": horas is not None and horas <= cfg["ALERTA_HORAS"],
            "copias": [{k: v for k, v in c.items() if k != "caminho"} for c in copias[:30]],
        }
    )
