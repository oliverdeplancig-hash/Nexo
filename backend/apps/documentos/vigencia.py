"""Vigência e revisão de documentos (ADR-015).

- Documento **revogado** continua no repositório (histórico, consulta), mas sai do contexto do assistente e
  da busca padrão; a tela mostra a revogação e o substituto (se a pessoa puder vê-lo).
- **Revisão periódica**: `revisar_em` marca a próxima revisão; quem mantém o documento é avisado a partir de
  NEXO_REVISAO["ANTECEDENCIA_DIAS"] antes e, enquanto atrasada, a cada NEXO_REVISAO["REPETIR_DIAS"].
"""

from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.contas.models import Funcao, Usuario

from .models import Documento, StatusDocumento, Vigencia


def hoje() -> date:
    return timezone.localdate()


def cfg() -> dict:
    return settings.NEXO_REVISAO


def filtro_revisao_pendente(ate: date | None = None) -> Q:
    limite = ate or (hoje() + timedelta(days=cfg()["ANTECEDENCIA_DIAS"]))
    return Q(
        vigencia=Vigencia.VIGENTE, status=StatusDocumento.DISPONIVEL, revisar_em__isnull=False, revisar_em__lte=limite
    )


def situacao_revisao(documento: Documento) -> str | None:
    """ "atrasada", "proxima" ou None."""
    if documento.vigencia != Vigencia.VIGENTE or not documento.revisar_em:
        return None
    if documento.revisar_em < hoje():
        return "atrasada"
    if documento.revisar_em <= hoje() + timedelta(days=cfg()["ANTECEDENCIA_DIAS"]):
        return "proxima"
    return None


def revogar(documento: Documento, *, motivo: str, substituido_por: Documento | None = None, em: date | None = None):
    documento.vigencia = Vigencia.REVOGADO
    documento.revogado_em = em or hoje()
    documento.motivo_revogacao = motivo.strip()[:500]
    documento.substituido_por = substituido_por
    documento.save(update_fields=["vigencia", "revogado_em", "motivo_revogacao", "substituido_por", "atualizado_em"])


def restabelecer(documento: Documento):
    documento.vigencia = Vigencia.VIGENTE
    documento.revogado_em = None
    documento.motivo_revogacao = ""
    documento.substituido_por = None
    documento.save(update_fields=["vigencia", "revogado_em", "motivo_revogacao", "substituido_por", "atualizado_em"])


def registrar_revisao(documento: Documento, proxima: date | None):
    documento.revisado_em = hoje()
    documento.revisar_em = proxima
    documento.revisao_avisada_em = None
    documento.save(update_fields=["revisado_em", "revisar_em", "revisao_avisada_em", "atualizado_em"])


def destinatarios(documento: Documento) -> list[Usuario]:
    """Responsável pela manutenção; sem ele, quem cadastrou; sem ambos, quem importa documentos no setor."""
    for candidato in (documento.responsavel, documento.criado_por):
        if candidato is not None and candidato.is_active:
            return [candidato]
    return [
        u
        for u in Usuario.objects.filter(is_active=True, setor=documento.setor_responsavel).prefetch_related("perfis")
        if u.tem_funcao(Funcao.IMPORTAR_DOCUMENTOS)
    ]


def avisar_revisoes() -> int:
    """Notifica revisões próximas ou atrasadas. Idempotente: pode rodar várias vezes ao dia."""
    from apps.notificacoes.servico import notificar

    agora = hoje()
    repetir = agora - timedelta(days=cfg()["REPETIR_DIAS"])
    pendentes = (
        Documento.objects.filter(filtro_revisao_pendente())
        .filter(Q(revisao_avisada_em__isnull=True) | Q(revisao_avisada_em__lte=repetir, revisar_em__lt=agora))
        .select_related("responsavel", "criado_por", "setor_responsavel")
    )
    enviados = 0
    for documento in pendentes:
        atrasada = documento.revisar_em < agora
        data_br = documento.revisar_em.strftime("%d/%m/%Y")
        for usuario in destinatarios(documento):
            notificar(
                usuario,
                "revisao_documento",
                f"Revisão {'atrasada' if atrasada else 'próxima'}: {documento.titulo}",
                f"A revisão {'estava prevista' if atrasada else 'está prevista'} para {data_br}. "
                "Confira se o documento continua válido e registre a revisão ou a revogação.",
                link=f"/documentos/{documento.id}",
                dados={"documento_id": documento.id},
            )
            enviados += 1
        documento.revisao_avisada_em = agora
        documento.save(update_fields=["revisao_avisada_em"])
    return enviados
