from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.ia.provedores import obter_provedor


@api_view(["GET"])
@permission_classes([AllowAny])
def saude(request):
    """Verificação simples para monitoramento (não expõe detalhes internos)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        banco = True
    except Exception:  # pragma: no cover - depende de infraestrutura
        banco = False
    return Response({"status": "ok" if banco else "degradado"}, status=200 if banco else 503)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def status_servicos(request):
    """Disponibilidade dos serviços exibida no cabeçalho do chat."""
    provedor = obter_provedor()
    return Response(
        {
            "ia_disponivel": provedor.disponivel(),
            "modelo_chat": settings.NEXO_IA["MODELO_CHAT"] if request.user.tem_funcao("ver_auditoria") else None,
            "motor_deterministico": True,
        }
    )


def aplicativo(request, *args, **kwargs):
    """index.html do frontend compilado, sem cache (o service worker e os assets cuidam do resto)."""
    from django.conf import settings
    from django.http import FileResponse, HttpResponse

    indice = settings.NEXO_FRONTEND_DIST / "index.html"
    if not indice.exists():
        return HttpResponse(
            "Telas do Nexo não encontradas. Gere com: cd frontend && npm run build",
            status=503,
            content_type="text/plain",
        )
    resposta = FileResponse(open(indice, "rb"), content_type="text/html; charset=utf-8")
    resposta["Cache-Control"] = "no-cache"
    return resposta
