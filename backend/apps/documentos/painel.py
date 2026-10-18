"""Painel do acervo e alertas de gestão (ADR-016).

Todos os números são calculados sobre `documentos_visiveis(usuario)` (ADR-005): o painel nunca conta nem lista
documento que a pessoa não pode consultar. Nenhum dado pessoal de quem consultou é exibido — só totais por
documento.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone

from apps.acesso.servico import documentos_visiveis
from apps.contas.models import Funcao, Usuario

from .models import Documento, StatusDocumento, Vigencia
from .vigencia import cfg as cfg_revisao
from .vigencia import hoje


def painel(usuario, dias: int = 30) -> dict:
    visiveis = documentos_visiveis(usuario)
    hj = hoje()
    limite = hj + timedelta(days=cfg_revisao()["ANTECEDENCIA_DIAS"])
    vigente_disponivel = Q(vigencia=Vigencia.VIGENTE, status=StatusDocumento.DISPONIVEL)

    resumo = visiveis.aggregate(
        total=Count("id"),
        vigentes=Count("id", filter=Q(vigencia=Vigencia.VIGENTE)),
        revogados=Count("id", filter=Q(vigencia=Vigencia.REVOGADO)),
        revisao_atrasada=Count("id", filter=vigente_disponivel & Q(revisar_em__lt=hj)),
        revisao_proxima=Count("id", filter=vigente_disponivel & Q(revisar_em__gte=hj, revisar_em__lte=limite)),
        sem_revisao=Count("id", filter=vigente_disponivel & Q(revisar_em__isnull=True)),
    )

    por_setor = list(
        visiveis.values("setor_responsavel__sigla", "setor_responsavel__nome")
        .annotate(
            vigentes=Count("id", filter=Q(vigencia=Vigencia.VIGENTE)),
            revogados=Count("id", filter=Q(vigencia=Vigencia.REVOGADO)),
            revisao_atrasada=Count("id", filter=vigente_disponivel & Q(revisar_em__lt=hj)),
            sem_revisao=Count("id", filter=vigente_disponivel & Q(revisar_em__isnull=True)),
            ultima_atualizacao=Max("atualizado_em"),
        )
        .order_by("setor_responsavel__sigla")
    )

    atrasadas = list(
        visiveis.filter(vigente_disponivel, revisar_em__lt=hj)
        .select_related("setor_responsavel", "responsavel")
        .order_by("revisar_em")[:20]
    )

    mais_consultados = _mais_consultados(visiveis, dias)
    return {
        "dias": dias,
        "resumo": resumo,
        "por_setor": [
            {
                "sigla": s["setor_responsavel__sigla"],
                "nome": s["setor_responsavel__nome"],
                "vigentes": s["vigentes"],
                "revogados": s["revogados"],
                "revisao_atrasada": s["revisao_atrasada"],
                "sem_revisao": s["sem_revisao"],
                "ultima_atualizacao": s["ultima_atualizacao"],
            }
            for s in por_setor
        ],
        "revisoes_atrasadas": [
            {
                "id": d.id,
                "titulo": d.titulo,
                "setor": d.setor_responsavel.sigla,
                "revisar_em": d.revisar_em,
                "dias_atraso": (hj - d.revisar_em).days,
                "responsavel": d.responsavel.nome_completo if d.responsavel else None,
            }
            for d in atrasadas
        ],
        "mais_consultados": mais_consultados,
    }


def _mais_consultados(visiveis, dias: int) -> list[dict]:
    """Aberturas de documento registradas na auditoria nos últimos `dias` (só contagens, sem quem abriu)."""
    from apps.auditoria.models import EventoAuditoria

    desde = timezone.now() - timedelta(days=dias)
    eventos = (
        EventoAuditoria.objects.filter(
            tipo="DOCUMENTO_ABERTO", objeto_tipo="Documento", ocorrido_em__gte=desde, resultado="SUCESSO"
        )
        .values("objeto_id")
        .annotate(n=Count("id"))
        .order_by("-n")[:200]
    )
    contagem = Counter({int(e["objeto_id"]): e["n"] for e in eventos if str(e["objeto_id"]).isdigit()})
    docs = {d.id: d for d in visiveis.filter(id__in=list(contagem)).select_related("setor_responsavel")}
    ordenados = [(i, n) for i, n in contagem.most_common() if i in docs][:10]
    return [
        {
            "id": i,
            "titulo": docs[i].titulo,
            "setor": docs[i].setor_responsavel.sigla,
            "vigencia": docs[i].vigencia,
            "aberturas": n,
        }
        for i, n in ordenados
    ]


def avisar_regras_com_fonte_revogada(documento: Documento) -> int:
    """Quando um documento é revogado, avisa quem mantém as regras publicadas que o citam como fonte.

    Destinatário: quem criou a regra (se ainda gere regras); senão, todos com a função `gerir_regras`."""
    from apps.motor.models import FonteRegra, StatusRegra
    from apps.notificacoes.servico import notificar

    regras = {
        f.regra_id: f.regra
        for f in FonteRegra.objects.filter(documento=documento, regra__status=StatusRegra.PUBLICADA).select_related(
            "regra"
        )
    }
    if not regras:
        return 0
    gestores = [
        u
        for u in Usuario.objects.filter(is_active=True).prefetch_related("perfis")
        if u.tem_funcao(Funcao.GERIR_REGRAS)
    ]
    enviados = 0
    for regra in regras.values():
        criador = next((u for u in gestores if u.id == regra.criada_por_id), None)
        for destinatario in [criador] if criador else gestores:
            notificar(
                destinatario,
                "regra_fonte_revogada",
                f"Regra {regra.codigo} com fonte revogada",
                f"O documento “{documento.titulo}” foi revogado. A regra “{regra.titulo}” continua respondendo com "
                "aviso até ser revisada.",
                link="/motor",
                dados={"regra": regra.codigo, "documento_id": documento.id},
            )
            enviados += 1
    return enviados
