from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ["id", "tipo", "titulo", "texto", "link", "lida", "criada_em"]


class NotificacaoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificacaoSerializer

    def get_queryset(self):
        qs = Notificacao.objects.filter(usuario=self.request.user)
        if self.request.query_params.get("nao_lidas") == "1":
            qs = qs.filter(lida=False)
        return qs

    @action(detail=False, methods=["get"])
    def contagem(self, request):
        return Response({"nao_lidas": Notificacao.objects.filter(usuario=request.user, lida=False).count()})

    @action(detail=True, methods=["post"])
    def ler(self, request, pk=None):
        self.get_queryset().filter(pk=pk).update(lida=True)
        return Response({"lida": True})

    @action(detail=False, methods=["post"], url_path="ler-todas")
    def ler_todas(self, request):
        total = self.get_queryset().filter(lida=False).update(lida=True)
        return Response({"atualizadas": total})
