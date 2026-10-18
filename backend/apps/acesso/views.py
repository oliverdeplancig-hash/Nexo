from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.auditoria.servico import registrar
from apps.contas.models import Funcao

from .models import Acao, AutorizacaoDocumento
from .servico import decidir, expandir


class AutorizacaoSerializer(serializers.ModelSerializer):
    destinatario = serializers.CharField(read_only=True)
    acoes_efetivas = serializers.SerializerMethodField()
    concedido_por_nome = serializers.CharField(source="concedido_por.nome_completo", default=None, read_only=True)

    class Meta:
        model = AutorizacaoDocumento
        fields = [
            "id",
            "documento",
            "usuario",
            "setor",
            "perfil",
            "destinatario",
            "acoes",
            "acoes_efetivas",
            "valido_ate",
            "motivo",
            "concedido_por_nome",
            "criado_em",
        ]

    def get_acoes_efetivas(self, obj):
        return sorted(expandir(obj.acoes))


def _documento_administravel(request, documento_id):
    from apps.documentos.models import Documento

    documento = get_object_or_404(Documento, pk=documento_id)
    decisao = decidir(request.user, documento)
    if not (decisao.permite(Acao.ADMINISTRAR) or request.user.tem_funcao(Funcao.ADMIN_PERMISSOES)):
        if not decisao.permite(Acao.CONSULTAR):
            raise Http404
        registrar(
            request, "FALHA_AUTORIZACAO", objeto=documento, resultado="NEGADO", detalhes={"operacao": "ver_matriz"}
        )
        raise PermissionDenied("Você não administra as permissões deste documento.")
    return documento


@api_view(["GET"])
def acoes(request):
    return Response([{"valor": a.value, "rotulo": a.label} for a in Acao])


@api_view(["GET"])
def minhas_permissoes(request, documento_id):
    """Ações do usuário atual sobre o documento, com os motivos (transparência)."""
    from apps.documentos.models import Documento

    documento = get_object_or_404(Documento, pk=documento_id)
    decisao = decidir(request.user, documento)
    if not decisao.permite(Acao.CONSULTAR):
        raise Http404
    return Response({"acoes": sorted(decisao.acoes), "motivos": decisao.motivos})


@api_view(["GET", "POST"])
def matriz(request, documento_id):
    """Matriz de permissões de um documento (tela 08)."""
    documento = _documento_administravel(request, documento_id)
    if request.method == "POST":
        serializer = AutorizacaoSerializer(data={**request.data, "documento": documento.id})
        serializer.is_valid(raise_exception=True)
        acoes_pedidas = set(serializer.validated_data["acoes"])
        if Acao.ADMINISTRAR in acoes_pedidas and not request.user.tem_funcao(Funcao.ADMIN_PERMISSOES):
            raise PermissionDenied("Conceder administração exige o perfil de administração de permissões.")
        try:
            autorizacao = serializer.save(concedido_por=request.user)
        except Exception as erro:
            return Response({"detail": str(erro)}, status=status.HTTP_400_BAD_REQUEST)
        registrar(
            request,
            "PERMISSAO_CONCEDIDA",
            objeto=documento,
            detalhes={"destinatario": autorizacao.destinatario, "acoes": autorizacao.acoes},
        )
        return Response(AutorizacaoSerializer(autorizacao).data, status=status.HTTP_201_CREATED)

    linhas = documento.autorizacoes.select_related("usuario", "setor", "perfil", "concedido_por")
    return Response(
        {
            "documento": {"id": documento.id, "titulo": documento.titulo, "classificacao": documento.classificacao},
            "acoes": [{"valor": a.value, "rotulo": a.label} for a in Acao],
            "autorizacoes": AutorizacaoSerializer(linhas, many=True).data,
        }
    )


@api_view(["DELETE"])
def revogar(request, autorizacao_id):
    autorizacao = get_object_or_404(AutorizacaoDocumento, pk=autorizacao_id)
    _documento_administravel(request, autorizacao.documento_id)
    detalhes = {"destinatario": autorizacao.destinatario, "acoes": autorizacao.acoes}
    documento = autorizacao.documento
    autorizacao.delete()
    registrar(request, "PERMISSAO_REVOGADA", objeto=documento, detalhes=detalhes)
    return Response(status=status.HTTP_204_NO_CONTENT)
