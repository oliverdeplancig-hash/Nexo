from django.utils.dateparse import parse_date
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.comum.permissoes import exige_funcao
from apps.contas.models import Funcao

from .models import EventoAuditoria, Resultado, TipoEvento
from .servico import verificar_integridade


class EventoSerializer(serializers.ModelSerializer):
    tipo_rotulo = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = EventoAuditoria
        fields = [
            "id",
            "ocorrido_em",
            "tipo",
            "tipo_rotulo",
            "resultado",
            "usuario_login",
            "setor_sigla",
            "objeto_tipo",
            "objeto_id",
            "objeto_descricao",
            "ip",
            "detalhes",
            "hash",
        ]


class EventoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventoSerializer
    permission_classes = [exige_funcao(Funcao.VER_AUDITORIA)]

    def get_queryset(self):
        qs = EventoAuditoria.objects.all()
        p = self.request.query_params
        if p.get("de") and parse_date(p["de"]):
            qs = qs.filter(ocorrido_em__date__gte=parse_date(p["de"]))
        if p.get("ate") and parse_date(p["ate"]):
            qs = qs.filter(ocorrido_em__date__lte=parse_date(p["ate"]))
        if p.get("usuario"):
            qs = qs.filter(usuario_login__icontains=p["usuario"])
        if p.get("setor"):
            qs = qs.filter(setor_sigla=p["setor"])
        if p.get("tipo"):
            qs = qs.filter(tipo__in=p["tipo"].split(","))
        if p.get("resultado"):
            qs = qs.filter(resultado=p["resultado"])
        return qs.order_by("-id")

    @action(detail=False, methods=["get"])
    def tipos(self, request):
        return Response(
            {
                "tipos": [{"valor": t.value, "rotulo": t.label} for t in TipoEvento],
                "resultados": [{"valor": r.value, "rotulo": r.label} for r in Resultado],
            }
        )

    @action(detail=False, methods=["get"], url_path="integridade")
    def integridade(self, request):
        return Response(verificar_integridade())
