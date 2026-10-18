from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria.servico import registrar
from apps.comum.permissoes import exige_funcao

from .diretorio import sugerir_setores
from .models import Setor
from .serializers import SetorEdicaoSerializer, SetorSerializer


class SetorViewSet(viewsets.ModelViewSet):
    """Diretório de setores. Leitura para todos; edição só para `gerir_setores`."""

    queryset = Setor.objects.filter(ativo=True)
    search_fields = ["nome", "sigla"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SetorEdicaoSerializer
        return SetorSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [exige_funcao("gerir_setores")()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        termo = self.request.query_params.get("q")
        if termo:
            qs = qs.filter(nome__icontains=termo) | qs.filter(sigla__icontains=termo)
        return qs.order_by("nome")

    def perform_create(self, serializer):
        setor = serializer.save()
        registrar(self.request, "ADMIN_SETOR", objeto=setor, detalhes={"acao": "criar"})

    def perform_update(self, serializer):
        setor = serializer.save()
        registrar(self.request, "ADMIN_SETOR", objeto=setor, detalhes={"acao": "alterar"})

    def perform_destroy(self, instance):
        # Setores são desativados, nunca apagados (preserva histórico e auditoria).
        instance.ativo = False
        instance.save(update_fields=["ativo"])
        registrar(self.request, "ADMIN_SETOR", objeto=instance, detalhes={"acao": "desativar"})

    @action(detail=False, methods=["get"], url_path="quem-pode-ajudar")
    def quem_pode_ajudar(self, request):
        pergunta = request.query_params.get("pergunta", "")
        sugestoes = sugerir_setores(pergunta, limite=5)
        dados = SetorSerializer([s.setor for s in sugestoes], many=True, context={"request": request}).data
        for item, sugestao in zip(dados, sugestoes, strict=True):
            item["pontuacao"] = sugestao.pontuacao
            item["termos_encontrados"] = list(sugestao.termos)
        return Response(dados)
