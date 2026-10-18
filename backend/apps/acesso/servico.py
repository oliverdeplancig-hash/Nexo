"""Motor de permissões documentais — determinístico e centralizado.

Regra de ouro: toda busca, listagem, abertura, download e todo contexto
entregue à IA passa por estas funções. Nenhum outro módulo decide acesso.

Composição das ações (ver docs/security/modelo-de-autorizacao.md):

1. Documento que não está DISPONÍVEL não é visível para ninguém além de
   quem o cadastrou, o responsável e quem administra o documento.
2. Responsável pelo documento e quem o cadastrou: todas as ações.
3. Classificação GERAL: todos os autenticados consultam e visualizam;
   baixar depende de `permite_download_geral`.
4. Classificação SETOR: membros do setor responsável consultam, visualizam e baixam.
5. Autorizações explícitas vigentes (usuário, setor do usuário ou perfil do usuário)
   somam as ações concedidas.
6. Ações implicam outras: administrar ⇒ todas; editar/baixar/compartilhar ⇒ visualizar;
   visualizar ⇒ consultar.

`is_superuser` NÃO concede acesso documental.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from .models import Acao, AutorizacaoDocumento, Classificacao

IMPLICACOES: dict[str, set[str]] = {
    Acao.ADMINISTRAR: set(Acao.values),
    Acao.EDITAR: {Acao.EDITAR, Acao.VISUALIZAR, Acao.CONSULTAR},
    Acao.BAIXAR: {Acao.BAIXAR, Acao.VISUALIZAR, Acao.CONSULTAR},
    Acao.COMPARTILHAR: {Acao.COMPARTILHAR, Acao.VISUALIZAR, Acao.CONSULTAR},
    Acao.VISUALIZAR: {Acao.VISUALIZAR, Acao.CONSULTAR},
    Acao.CONSULTAR: {Acao.CONSULTAR},
}


def expandir(acoes) -> set[str]:
    resultado: set[str] = set()
    for acao in acoes:
        resultado |= IMPLICACOES.get(acao, set())
    return resultado


@dataclass
class Decisao:
    acoes: set[str] = field(default_factory=set)
    motivos: list[str] = field(default_factory=list)

    def permite(self, acao: str) -> bool:
        return acao in self.acoes


def _autorizacoes_vigentes(usuario) -> Q:
    agora = timezone.now()
    perfis = list(usuario.perfis.values_list("id", flat=True))
    destino = Q(usuario=usuario)
    if usuario.setor_id:
        destino |= Q(setor_id=usuario.setor_id)
    if perfis:
        destino |= Q(perfil_id__in=perfis)
    return destino & (Q(valido_ate__isnull=True) | Q(valido_ate__gt=agora))


def decidir(usuario, documento) -> Decisao:
    """Ações que `usuario` pode executar em `documento`, com os motivos."""
    from apps.documentos.models import StatusDocumento

    decisao = Decisao()
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        decisao.motivos.append("usuário não autenticado ou inativo")
        return decisao

    eh_dono = usuario.id in (documento.responsavel_id, documento.criado_por_id)
    if eh_dono:
        decisao.acoes |= set(Acao.values)
        decisao.motivos.append("responsável ou autor do cadastro")

    explicitas = AutorizacaoDocumento.objects.filter(_autorizacoes_vigentes(usuario), documento=documento)
    for aut in explicitas:
        decisao.acoes |= expandir(aut.acoes)
        decisao.motivos.append(f"autorização explícita ({aut.destinatario})")

    if documento.status != StatusDocumento.DISPONIVEL:
        # Fora do ar: só quem cadastrou, o responsável ou quem administra.
        if not eh_dono and Acao.ADMINISTRAR not in decisao.acoes:
            return Decisao(motivos=["documento ainda não disponibilizado"])
        return decisao

    if documento.classificacao == Classificacao.GERAL:
        base = {Acao.CONSULTAR, Acao.VISUALIZAR}
        if documento.permite_download_geral:
            base.add(Acao.BAIXAR)
        decisao.acoes |= base
        decisao.motivos.append("classificação geral")
    elif documento.classificacao == Classificacao.SETOR and usuario.setor_id == documento.setor_responsavel_id:
        decisao.acoes |= expandir([Acao.BAIXAR])
        decisao.motivos.append("membro do setor responsável")

    return decisao


def pode(usuario, acao: str, documento) -> bool:
    return decidir(usuario, documento).permite(acao)


def documentos_visiveis(usuario, acao: str = Acao.CONSULTAR, queryset: QuerySet | None = None) -> QuerySet:
    """Filtro de banco equivalente a `decidir(...).permite(acao)` para listas.

    Aplicado ANTES de qualquer ordenação por relevância, para que a busca e a IA
    nunca vejam documentos não autorizados — nem mesmo em contagens.
    """
    from apps.documentos.models import Documento, StatusDocumento

    qs = queryset if queryset is not None else Documento.objects.all()
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return qs.none()

    concede = [a for a, implicadas in IMPLICACOES.items() if acao in implicadas]
    explicita = AutorizacaoDocumento.objects.filter(_autorizacoes_vigentes(usuario), documento=OuterRef("pk"))
    cond_explicita = Q()
    for a in concede:
        cond_explicita |= Q(acoes__contains=[a])
    explicita = explicita.filter(cond_explicita)

    dono = Q(responsavel=usuario) | Q(criado_por=usuario)
    disponivel = Q(status=StatusDocumento.DISPONIVEL)

    if acao in (Acao.CONSULTAR, Acao.VISUALIZAR):
        geral = Q(classificacao=Classificacao.GERAL)
    elif acao == Acao.BAIXAR:
        geral = Q(classificacao=Classificacao.GERAL, permite_download_geral=True)
    else:
        geral = Q(pk__in=[])

    if acao in (Acao.CONSULTAR, Acao.VISUALIZAR, Acao.BAIXAR) and usuario.setor_id:
        setor = Q(classificacao=Classificacao.SETOR, setor_responsavel_id=usuario.setor_id)
    else:
        setor = Q(pk__in=[])

    # Autorização com "administrar" alcança documentos ainda não disponíveis.
    administra = AutorizacaoDocumento.objects.filter(
        _autorizacoes_vigentes(usuario), documento=OuterRef("pk"), acoes__contains=[Acao.ADMINISTRAR]
    )

    return (
        qs.annotate(_explicita=Exists(explicita), _administra=Exists(administra))
        .filter(dono | Q(_administra=True) | (disponivel & (geral | setor | Q(_explicita=True))))
        .distinct()
    )
