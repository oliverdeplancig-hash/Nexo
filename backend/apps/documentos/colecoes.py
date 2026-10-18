"""Regras das coleções (pastas) — ADR-013. Uma coleção agrupa documentos e NUNCA altera permissões (ADR-005).

- Coleção pessoal: só quem criou vê, edita, exclui e organiza.
- Coleção institucional: todos veem; editar, excluir e organizar exige a função `gerir_colecoes`.
- Só entram numa coleção documentos que a pessoa pode consultar; quem abre a coleção continua vendo
  apenas os documentos autorizados para si.
"""

from django.db.models import Q

from apps.contas.models import Funcao

from .models import Colecao


def filtro_visiveis(usuario) -> Q:
    return Q(pessoal=False) | Q(criada_por=usuario)


def visiveis(usuario):
    return Colecao.objects.filter(filtro_visiveis(usuario))


def pode_gerir(usuario, colecao: Colecao) -> bool:
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return False
    if colecao.pessoal:
        return colecao.criada_por_id == usuario.id
    return usuario.tem_funcao(Funcao.GERIR_COLECOES)


def gerenciaveis(usuario, ids) -> list[Colecao]:
    """Das coleções pedidas, as que a pessoa pode organizar (as demais são ignoradas)."""
    return [c for c in visiveis(usuario).filter(id__in=list(ids or [])) if pode_gerir(usuario, c)]


def substituir_do_documento(usuario, documento, ids_pedidos) -> None:
    """Troca as coleções do documento só entre as que a pessoa organiza; as outras ficam como estão."""
    pedidas = {c.id for c in gerenciaveis(usuario, ids_pedidos)}
    atuais = list(documento.colecoes.all())
    alheias = {c.id for c in atuais if not pode_gerir(usuario, c)}
    documento.colecoes.set(alheias | pedidas)
