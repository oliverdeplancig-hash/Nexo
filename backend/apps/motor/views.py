from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria.servico import registrar
from apps.comum.permissoes import exige_funcao
from apps.contas.models import Funcao

from .models import Regra, StatusRegra, VersaoRegra
from .motor import avaliar, regras_aplicaveis, renderizar
from .serializers import RegraSerializer, VersaoRegraSerializer


class RegraViewSet(viewsets.ModelViewSet):
    """Cadastro e publicação das regras do motor determinístico."""

    serializer_class = RegraSerializer
    permission_classes = [exige_funcao(Funcao.GERIR_REGRAS)]

    def get_queryset(self):
        qs = Regra.objects.select_related("setor_responsavel").prefetch_related(
            "fontes__documento", "setores_alvo", "perfis_alvo"
        )
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("q"):
            termo = self.request.query_params["q"]
            qs = qs.filter(titulo__icontains=termo) | qs.filter(codigo__icontains=termo)
        return qs.order_by("codigo")

    def perform_create(self, serializer):
        regra = serializer.save(criada_por=self.request.user)
        registrar(self.request, "ADMIN_REGRA", objeto=regra, detalhes={"acao": "criar"})

    def perform_update(self, serializer):
        regra = serializer.save()
        # Editar uma regra publicada a devolve para rascunho até nova publicação.
        if regra.status == StatusRegra.PUBLICADA:
            regra.status = StatusRegra.RASCUNHO
            regra.save(update_fields=["status"])
        registrar(self.request, "ADMIN_REGRA", objeto=regra, detalhes={"acao": "alterar"})

    def perform_destroy(self, instance):
        instance.status = StatusRegra.ARQUIVADA
        instance.save(update_fields=["status"])
        registrar(self.request, "ADMIN_REGRA", objeto=instance, detalhes={"acao": "arquivar"})

    @action(detail=True, methods=["post"])
    def publicar(self, request, pk=None):
        regra = self.get_object()
        with transaction.atomic():
            regra.versao += 1
            regra.status = StatusRegra.PUBLICADA
            regra.publicada_em = timezone.now()
            regra.publicada_por = request.user
            regra.save()
            VersaoRegra.objects.create(
                regra=regra, versao=regra.versao, conteudo=RegraSerializer(regra).data, publicada_por=request.user
            )
        registrar(request, "ADMIN_REGRA", objeto=regra, detalhes={"acao": "publicar", "versao": regra.versao})
        return Response(RegraSerializer(regra).data)

    @action(detail=True, methods=["get"])
    def versoes(self, request, pk=None):
        return Response(VersaoRegraSerializer(self.get_object().versoes.all(), many=True).data)

    @action(detail=False, methods=["post"])
    def simular(self, request):
        """Mostra como o motor decidiria a pergunta, com o rastro completo.

        `incluir_rascunho`: id de uma regra em rascunho para testá-la junto às publicadas.
        """
        pergunta = (request.data.get("pergunta") or "")[:1000]
        regras = regras_aplicaveis(request.user)
        rascunho_id = request.data.get("incluir_rascunho")
        if rascunho_id:
            rascunho = Regra.objects.filter(pk=rascunho_id).first()
            if rascunho and rascunho not in regras:
                regras.append(rascunho)
        resultado = avaliar(pergunta, request.user, regras=regras)
        resposta = {
            "decisao": resultado.decisao,
            "pontuacao": resultado.pontuacao,
            "rastro": resultado.rastro,
            "alternativas": [c.resumo() for c in resultado.alternativas],
        }
        if resultado.regra:
            resposta["regra"] = {
                "id": resultado.regra.id,
                "codigo": resultado.regra.codigo,
                "titulo": resultado.regra.titulo,
            }
            resposta["resposta"] = renderizar(resultado.regra, request.user)
        return Response(resposta)
