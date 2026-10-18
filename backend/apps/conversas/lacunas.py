"""Avaliação das respostas e lacunas do assistente (ADR-012).

- O autor da pergunta avalia a resposta (útil / não útil, motivo e comentário).
- Quem gere as regras do motor vê as **lacunas**: respostas sem fontes suficientes, respostas só com trechos
  (IA indisponível) e respostas avaliadas como não úteis — para criar ou ajustar regras.

Privacidade e sigilo (ver docs/security/modelo-de-autorizacao.md):
- a lista de lacunas **não identifica** quem perguntou (nem nome, nem setor);
- o **conteúdo da resposta não é mostrado** (pode conter trechos de documentos que o gestor não pode ler);
- documentos usados como fonte só aparecem se o gestor puder consultá-los (motor de permissões, ADR-005);
- apagar a conversa apaga a pergunta, a avaliação e a lacuna.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.acesso.models import Acao
from apps.acesso.servico import decidir
from apps.auditoria.servico import registrar
from apps.comum.paginacao import PaginacaoPadrao
from apps.comum.permissoes import exige_funcao
from apps.contas.models import Funcao
from apps.motor.models import Regra

from .models import AvaliacaoResposta, Mensagem, MotivoAvaliacao, Origem, TratamentoLacuna

ORIGENS_LACUNA = (Origem.SEM_FONTES, Origem.EXTRATIVO)


# --------------------------------------------------------------------------
# Avaliação pelo autor
# --------------------------------------------------------------------------
class AvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvaliacaoResposta
        fields = ["util", "motivo", "comentario", "atualizada_em"]
        read_only_fields = ["atualizada_em"]

    def validate(self, dados):
        if dados.get("util"):
            dados["motivo"] = ""
        return dados


def serializar_avaliacao(mensagem: Mensagem) -> dict | None:
    try:
        return AvaliacaoSerializer(mensagem.avaliacao).data
    except AvaliacaoResposta.DoesNotExist:
        return None


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def avaliar(request, pk: int):
    """Só o autor avalia, e só respostas do assistente. Mensagem de outra pessoa → 404."""
    mensagem = get_object_or_404(Mensagem, pk=pk, conversa__usuario=request.user, papel=Mensagem.Papel.ASSISTENTE)
    if request.method == "DELETE":
        AvaliacaoResposta.objects.filter(mensagem=mensagem).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    existente = AvaliacaoResposta.objects.filter(mensagem=mensagem).first()
    serializer = AvaliacaoSerializer(existente, data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(mensagem=mensagem)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def motivos(request):
    return Response([{"valor": m.value, "rotulo": m.label} for m in MotivoAvaliacao])


# --------------------------------------------------------------------------
# Lacunas (gestão do motor)
# --------------------------------------------------------------------------
def _lacunas_base():
    pergunta = Mensagem.objects.filter(
        conversa=OuterRef("conversa"), papel=Mensagem.Papel.USUARIO, id__lt=OuterRef("id")
    ).order_by("-id")
    return (
        Mensagem.objects.filter(papel=Mensagem.Papel.ASSISTENTE)
        .filter(Q(origem__in=ORIGENS_LACUNA) | Q(avaliacao__util=False))
        .annotate(pergunta=Subquery(pergunta.values("conteudo")[:1]))
        .select_related("avaliacao", "tratamento", "tratamento__tratada_por", "tratamento__regra")
        .order_by("-criada_em", "-id")
    )


def _fontes_visiveis(mensagem: Mensagem, usuario) -> list[dict]:
    from apps.documentos.models import Documento

    ids = {f["documento_id"] for f in mensagem.fontes or [] if f.get("citada", True)}
    if not ids:
        return []
    saida = []
    for doc in Documento.objects.filter(id__in=ids):
        if decidir(usuario, doc).permite(Acao.CONSULTAR):
            saida.append({"documento_id": doc.id, "titulo": doc.titulo})
    return sorted(saida, key=lambda d: d["titulo"])


def _item(mensagem: Mensagem, usuario) -> dict:
    rastro = mensagem.rastro or {}
    candidatos = (rastro.get("motor") or {}).get("candidatos") or []
    proxima = candidatos[0] if candidatos and not rastro.get("regra") else None
    try:
        tratamento = mensagem.tratamento
    except TratamentoLacuna.DoesNotExist:
        tratamento = None
    return {
        "id": mensagem.id,
        "pergunta": mensagem.pergunta or "",
        "origem": mensagem.origem,
        "criada_em": mensagem.criada_em,
        "avaliacao": serializar_avaliacao(mensagem),
        "regra_usada": (rastro.get("regra") or {}).get("codigo"),
        "regra_proxima": (
            {"codigo": proxima["codigo"], "titulo": proxima.get("titulo", ""), "pontuacao": proxima["pontuacao"]}
            if proxima
            else None
        ),
        "fontes": _fontes_visiveis(mensagem, usuario),
        "tratamento": (
            {
                "tratada_em": tratamento.tratada_em,
                "tratada_por": tratamento.tratada_por.nome_completo if tratamento.tratada_por else "",
                "observacao": tratamento.observacao,
                "regra": tratamento.regra.codigo if tratamento.regra else None,
            }
            if tratamento
            else None
        ),
    }


@api_view(["GET"])
@permission_classes([exige_funcao(Funcao.GERIR_REGRAS)])
def lacunas(request):
    """Filtros: situacao=pendentes|tratadas|todas · tipo=todas|negativas|sem_resposta · dias (padrão 90)."""
    qs = _lacunas_base()
    situacao = request.query_params.get("situacao", "pendentes")
    if situacao == "pendentes":
        qs = qs.filter(tratamento__isnull=True)
    elif situacao == "tratadas":
        qs = qs.filter(tratamento__isnull=False)
    tipo = request.query_params.get("tipo", "todas")
    if tipo == "negativas":
        qs = qs.filter(avaliacao__util=False)
    elif tipo == "sem_resposta":
        qs = qs.filter(origem__in=ORIGENS_LACUNA)
    try:
        dias = max(1, min(int(request.query_params.get("dias", 90)), 3650))
    except ValueError:
        dias = 90
    qs = qs.filter(criada_em__gte=timezone.now() - timedelta(days=dias))
    termo = request.query_params.get("q", "").strip()
    if termo:
        qs = qs.filter(pergunta__icontains=termo)

    paginador = PaginacaoPadrao()
    pagina = paginador.paginate_queryset(qs, request)
    return paginador.get_paginated_response([_item(m, request.user) for m in pagina])


@api_view(["GET"])
@permission_classes([exige_funcao(Funcao.GERIR_REGRAS)])
def resumo(request):
    """Indicadores dos últimos N dias (padrão 30)."""
    try:
        dias = max(1, min(int(request.query_params.get("dias", 30)), 3650))
    except ValueError:
        dias = 30
    respostas = Mensagem.objects.filter(
        papel=Mensagem.Papel.ASSISTENTE, criada_em__gte=timezone.now() - timedelta(days=dias)
    ).exclude(origem=Origem.ERRO)
    por_origem = dict(respostas.values_list("origem").annotate(n=Count("id")).values_list("origem", "n"))
    avaliadas = respostas.filter(avaliacao__isnull=False)
    return Response(
        {
            "dias": dias,
            "respostas": respostas.count(),
            "por_origem": por_origem,
            "avaliadas": avaliadas.count(),
            "uteis": avaliadas.filter(avaliacao__util=True).count(),
            "nao_uteis": avaliadas.filter(avaliacao__util=False).count(),
            "lacunas_pendentes": _lacunas_base().filter(tratamento__isnull=True).count(),
        }
    )


@api_view(["POST", "DELETE"])
@permission_classes([exige_funcao(Funcao.GERIR_REGRAS)])
def tratar(request, pk: int):
    mensagem = get_object_or_404(_lacunas_base(), pk=pk)
    if request.method == "DELETE":
        TratamentoLacuna.objects.filter(mensagem=mensagem).delete()
        registrar(request, "LACUNA_TRATADA", objeto=mensagem, detalhes={"acao": "reabrir"})
        return Response(status=status.HTTP_204_NO_CONTENT)
    regra = None
    if request.data.get("regra"):
        regra = get_object_or_404(Regra, pk=request.data["regra"])
    observacao = str(request.data.get("observacao", ""))[:500]
    TratamentoLacuna.objects.update_or_create(
        mensagem=mensagem, defaults={"tratada_por": request.user, "observacao": observacao, "regra": regra}
    )
    registrar(
        request,
        "LACUNA_TRATADA",
        objeto=mensagem,
        detalhes={"acao": "tratar", "regra": regra.codigo if regra else None},
    )
    mensagem = _lacunas_base().get(pk=pk)
    return Response(_item(mensagem, request.user))
