from asgiref.sync import async_to_sync
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Conversa
from .orquestrador import ErroConversa, executar
from .serializers import ConversaSerializer, MensagemSerializer


class ConversaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Histórico de conversas. Cada usuário só enxerga as próprias."""

    serializer_class = ConversaSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Conversa.objects.filter(usuario=self.request.user).select_related("documento_contexto")
        if self.request.query_params.get("arquivadas") != "1":
            qs = qs.filter(arquivada=False)
        if self.request.query_params.get("q"):
            qs = qs.filter(titulo__icontains=self.request.query_params["q"])
        return qs

    @action(detail=True, methods=["get"])
    def mensagens(self, request, pk=None):
        conversa = self.get_object()
        return Response(MensagemSerializer(conversa.mensagens.all(), many=True, context={"request": request}).data)

    @action(detail=False, methods=["post"])
    def perguntar(self, request):
        """Alternativa REST (sem streaming) ao WebSocket. Útil para integrações e testes."""
        eventos = []

        async def _coletar(evento):
            if evento["tipo"] != "token":
                eventos.append(evento)

        try:
            async_to_sync(executar)(
                request.user,
                request.data.get("conversa_id"),
                request.data.get("texto", ""),
                _coletar,
                documento_id=request.data.get("documento_id"),
            )
        except ErroConversa as erro:
            return Response({"codigo": erro.codigo, "detail": erro.mensagem}, status=status.HTTP_400_BAD_REQUEST)
        resposta = next(e for e in eventos if e["tipo"] == "resposta")
        return Response({**resposta, "eventos": [e for e in eventos if e["tipo"] in ("status", "aviso")]})
