from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.auditoria.servico import registrar
from apps.documentos.models import Documento, Favorito
from apps.documentos.serializers import DocumentoListaSerializer

from .servico import agrupar_por_documento, buscar_trechos

MODOS = {"hibrida", "texto", "semantica", "nome"}


@api_view(["GET"])
def buscar(request):
    """Tela 05 — busca inteligente. Só conta e mostra o que o usuário pode consultar."""
    p = request.query_params
    consulta = (p.get("q") or "").strip()[:500]
    modo = p.get("modo") if p.get("modo") in MODOS else "hibrida"
    filtros = {k: p.get(k) for k in ("tipo", "setor", "categoria", "palavra_chave", "de", "ate") if p.get(k)}

    if not consulta:
        return Response({"consulta": "", "total_documentos": 0, "resultados": [], "facetas": {}})

    resultados, diagnostico = buscar_trechos(request.user, consulta, filtros=filtros, modo=modo, limite=60)
    grupos = agrupar_por_documento(resultados)
    contexto = {
        "request": request,
        "favoritos": set(Favorito.objects.filter(usuario=request.user).values_list("documento_id", flat=True)),
    }
    saida = []
    for grupo in grupos:
        saida.append(
            {
                "documento": DocumentoListaSerializer(grupo["documento"], context=contexto).data,
                "pontuacao": round(grupo["pontuacao"], 5),
                "trechos": [
                    {
                        "id": r.trecho.id,
                        "pagina": r.trecho.pagina,
                        "secao": r.trecho.secao,
                        "destaque": r.destaque,
                        "origens": r.origens,
                        "similaridade": r.similaridade,
                    }
                    for r in grupo["trechos"][:3]
                ],
            }
        )

    # Facetas calculadas apenas sobre documentos autorizados e encontrados.
    ids = [g["documento"].id for g in grupos]
    docs = Documento.objects.filter(id__in=ids)  # ids já vieram do filtro de permissões
    facetas = {
        "tipo": list(docs.values("tipo_arquivo").annotate(total=Count("id", distinct=True)).order_by("tipo_arquivo")),
        "setor": list(
            docs.values("setor_responsavel_id", "setor_responsavel__sigla")
            .annotate(total=Count("id", distinct=True))
            .order_by("setor_responsavel__sigla")
        ),
        "categoria": list(
            docs.exclude(categoria=None)
            .values("categoria_id", "categoria__nome")
            .annotate(total=Count("id", distinct=True))
            .order_by("categoria__nome")
        ),
    }
    registrar(
        request,
        "BUSCA",
        detalhes={
            "modo": modo,
            "tamanho_consulta": len(consulta),
            "documentos": len(grupos),
            "filtros": sorted(filtros),
        },
    )
    return Response(
        {
            "consulta": consulta,
            "modo": modo,
            "total_documentos": len(saida),
            "resultados": saida,
            "facetas": facetas,
            "semantica_disponivel": diagnostico["semantica_disponivel"],
        }
    )
