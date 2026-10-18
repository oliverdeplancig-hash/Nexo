"""Busca híbrida: texto completo (PostgreSQL) + semântica (pgvector) + nome.

O conjunto de documentos é filtrado pelo motor de permissões ANTES de
qualquer ranqueamento. Resultados são fundidos por Reciprocal Rank Fusion,
com desempate pelo id do trecho (resultado estável para a mesma entrada).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank
from django.db.models import F, Q
from django.utils.dateparse import parse_date
from pgvector.django import CosineDistance

from apps.acesso.models import Acao
from apps.acesso.servico import documentos_visiveis
from apps.comum import texto
from apps.comum.banco import tem_unaccent
from apps.documentos.models import Documento, Trecho
from apps.ia.provedores import ProvedorIndisponivel, obter_provedor

CONFIG_FTS = "nexo_pt"
K_RRF = 60
MARCA_INICIO = "\u0002"
MARCA_FIM = "\u0003"


@dataclass
class Resultado:
    trecho: Trecho
    pontuacao: float = 0.0
    rank_texto: float = 0.0
    similaridade: float | None = None
    destaque: str = ""
    origens: list[str] = field(default_factory=list)


def consulta_tsquery(consulta: str) -> SearchQuery | None:
    """Termos unidos por OU (perguntas em linguagem natural raramente casam com E).

    Cada termo entra com e sem acento: funciona com a configuração `nexo_pt`
    com unaccent (servidor) e sem ela (PostgreSQL embutido local).
    """
    minusculas = re.sub(r"[^\w\s]", " ", consulta.lower()).split()
    termos: list[str] = []
    for palavra in minusculas:
        sem_acento = texto.remover_acentos(palavra)
        if sem_acento in texto.STOPWORDS or len(sem_acento) < 2:
            continue
        for forma in (palavra, sem_acento):
            if forma not in termos:
                termos.append(forma)
    if not termos:
        return None
    return SearchQuery(" | ".join(termos[:30]), config=CONFIG_FTS, search_type="raw")


def documentos_filtrados(usuario, filtros: dict | None = None, documento_id: int | None = None):
    qs = documentos_visiveis(usuario, Acao.CONSULTAR)
    f = filtros or {}
    if documento_id:
        qs = qs.filter(id=documento_id)
    if f.get("tipo"):
        qs = qs.filter(tipo_arquivo__in=_lista(f["tipo"]))
    if f.get("setor"):
        qs = qs.filter(setor_responsavel_id__in=_lista(f["setor"]))
    if f.get("categoria"):
        qs = qs.filter(categoria_id__in=_lista(f["categoria"]))
    if f.get("palavra_chave"):
        for palavra in _lista(f["palavra_chave"]):
            qs = qs.filter(palavras_chave__icontains=palavra)
    if f.get("de") and parse_date(str(f["de"])):
        qs = qs.filter(data_documento__gte=parse_date(str(f["de"])))
    if f.get("ate") and parse_date(str(f["ate"])):
        qs = qs.filter(data_documento__lte=parse_date(str(f["ate"])))
    return qs


def _lista(valor) -> list[str]:
    if isinstance(valor, (list, tuple)):
        return [str(v) for v in valor]
    return [v for v in str(valor).split(",") if v]


def buscar_trechos(
    usuario,
    consulta: str,
    *,
    filtros: dict | None = None,
    documento_id: int | None = None,
    modo: str = "hibrida",
    limite: int = 20,
) -> tuple[list[Resultado], dict]:
    """Retorna (resultados, diagnóstico). O diagnóstico vai para o rastro da resposta."""
    docs = documentos_filtrados(usuario, filtros, documento_id)
    base = Trecho.objects.filter(documento__in=docs.values("id")).select_related(
        "documento", "documento__setor_responsavel"
    )
    candidatos: dict[int, Resultado] = {}
    diagnostico = {"modo": modo, "texto": 0, "semantica": 0, "nome": 0, "semantica_disponivel": None}

    def _somar(trecho: Trecho, posicao: int, origem: str) -> Resultado:
        r = candidatos.setdefault(trecho.id, Resultado(trecho=trecho))
        r.pontuacao += 1.0 / (K_RRF + posicao)
        r.origens.append(origem)
        return r

    tsquery = consulta_tsquery(consulta)
    if modo in ("hibrida", "texto") and tsquery is not None:
        por_texto = (
            base.filter(busca=tsquery)
            .annotate(rank=SearchRank(F("busca"), tsquery, cover_density=True, normalization=32))
            .order_by("-rank", "id")[:50]
        )
        for posicao, trecho in enumerate(por_texto, start=1):
            _somar(trecho, posicao, "texto").rank_texto = float(trecho.rank)
        diagnostico["texto"] = len(por_texto)

    if modo in ("hibrida", "semantica") and consulta.strip():
        try:
            vetor = obter_provedor().embed([consulta])[0]
            diagnostico["semantica_disponivel"] = True
            por_vetor = (
                base.filter(embedding__isnull=False)
                .annotate(distancia=CosineDistance("embedding", vetor))
                .order_by("distancia", "id")[:50]
            )
            for posicao, trecho in enumerate(por_vetor, start=1):
                _somar(trecho, posicao, "semantica").similaridade = round(1 - float(trecho.distancia), 4)
            diagnostico["semantica"] = len(por_vetor)
        except ProvedorIndisponivel:
            diagnostico["semantica_disponivel"] = False

    if modo in ("hibrida", "nome") and consulta.strip():
        # Sem unaccent, o título é comparado com a grafia digitada (com acentos).
        base_termos = texto.normalizar(consulta) if tem_unaccent() else re.sub(r"[^\w\s]", " ", consulta.lower())
        termos = [t for t in base_termos.split() if len(t) > 2 and texto.remover_acentos(t) not in texto.STOPWORDS]
        if termos:
            campo_titulo = (
                "documento__titulo__unaccent__icontains" if tem_unaccent() else "documento__titulo__icontains"
            )
            cond = Q()
            for t in termos[:6]:
                cond &= Q(**{campo_titulo: t}) | Q(documento__numero_referencia__icontains=t)
            por_nome = base.filter(cond).order_by("documento_id", "ordem").distinct("documento_id")[:20]
            for posicao, trecho in enumerate(por_nome, start=1):
                _somar(trecho, posicao, "nome")
            diagnostico["nome"] = len(por_nome)

    resultados = sorted(candidatos.values(), key=lambda r: (-r.pontuacao, r.trecho.id))[:limite]
    _anexar_destaques(resultados, tsquery)
    return resultados, diagnostico


def _anexar_destaques(resultados: list[Resultado], tsquery: SearchQuery | None) -> None:
    if not resultados:
        return
    if tsquery is None:
        for r in resultados:
            r.destaque = r.trecho.texto[:300]
        return
    destaques = dict(
        Trecho.objects.filter(id__in=[r.trecho.id for r in resultados])
        .annotate(
            destaque=SearchHeadline(
                "texto",
                tsquery,
                config=CONFIG_FTS,
                start_sel=MARCA_INICIO,
                stop_sel=MARCA_FIM,
                max_words=45,
                min_words=20,
                max_fragments=2,
                fragment_delimiter=" … ",
            )
        )
        .values_list("id", "destaque")
    )
    for r in resultados:
        r.destaque = destaques.get(r.trecho.id) or r.trecho.texto[:300]


def evidencia_suficiente(resultados: list[Resultado]) -> bool:
    """Há base documental mínima para a IA responder?

    Basta um trecho encontrado por texto completo ou um trecho com similaridade
    semântica acima do mínimo configurado.
    """
    minimo = settings.NEXO_IA["SIMILARIDADE_MINIMA"]
    return any("texto" in r.origens or (r.similaridade is not None and r.similaridade >= minimo) for r in resultados)


def agrupar_por_documento(resultados: list[Resultado]) -> list[dict]:
    grupos: dict[int, dict] = {}
    for r in resultados:
        doc: Documento = r.trecho.documento
        grupo = grupos.setdefault(doc.id, {"documento": doc, "pontuacao": 0.0, "trechos": []})
        grupo["pontuacao"] = max(grupo["pontuacao"], r.pontuacao)
        grupo["trechos"].append(r)
    return sorted(grupos.values(), key=lambda g: (-g["pontuacao"], g["documento"].id))
