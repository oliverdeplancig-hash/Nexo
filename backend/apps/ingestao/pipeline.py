"""Pipeline de ingestão: recebido → extração → metadados → indexação → disponível.

O documento só entra em busca e chat quando chega a DISPONÍVEL, depois de
indexado e com as permissões já gravadas (elas são criadas no upload).
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.auditoria.servico import registrar
from apps.documentos.models import Documento, StatusDocumento, Trecho
from apps.ia.provedores import ProvedorIndisponivel, obter_provedor
from apps.notificacoes.servico import enviar_evento, notificar

from .extratores import FalhaExtracao, extrair
from .fatiamento import fatiar, sugerir_palavras_chave, sugerir_referencia
from .models import EtapaProcessamento

logger = logging.getLogger("nexo.ingestao")

LOTE_EMBEDDING = 16

SQL_TSVECTOR = """
UPDATE documentos_trecho t
   SET busca = setweight(to_tsvector('nexo_pt', coalesce(d.titulo, '')), 'A')
            || setweight(to_tsvector('nexo_pt', coalesce(t.secao, '')), 'B')
            || setweight(to_tsvector('nexo_pt', t.texto), 'C')
  FROM documentos_documento d
 WHERE d.id = t.documento_id AND d.id = %s
"""


def _etapa(documento: Documento, status: str, situacao: str = "ok", mensagem: str = "") -> None:
    if status not in (StatusDocumento.FALHA,):
        documento.status = status
        documento.save(update_fields=["status", "atualizado_em"])
    EtapaProcessamento.objects.create(documento=documento, etapa=status, situacao=situacao, mensagem=mensagem[:500])
    if documento.criado_por_id:
        enviar_evento(
            documento.criado_por_id,
            {
                "tipo": "processamento",
                "documento_id": documento.id,
                "status": documento.status,
                "etapa": status,
                "situacao": situacao,
                "mensagem": mensagem,
            },
        )


def processar(documento: Documento) -> Documento:
    cfg = settings.NEXO_INGESTAO
    try:
        _etapa(documento, StatusDocumento.EXTRAINDO)
        with documento.arquivo.open("rb") as arquivo:
            conteudo = arquivo.read()
        blocos = extrair(conteudo, "." + documento.tipo_arquivo)

        _etapa(documento, StatusDocumento.METADADOS)
        texto_completo = "\n".join(b.texto for b in blocos)
        paginas = [b.pagina for b in blocos if b.pagina]
        documento.total_paginas = max(paginas) if paginas else None
        if not documento.palavras_chave:
            documento.palavras_chave = sugerir_palavras_chave(texto_completo)
        if not documento.numero_referencia:
            documento.numero_referencia = sugerir_referencia(texto_completo)
        documento.save(update_fields=["total_paginas", "palavras_chave", "numero_referencia", "atualizado_em"])

        _etapa(documento, StatusDocumento.INDEXANDO)
        gerados = fatiar(blocos, cfg["TAMANHO_TRECHO"], cfg["SOBREPOSICAO"])
        with transaction.atomic():
            documento.trechos.all().delete()
            Trecho.objects.bulk_create(
                [
                    Trecho(documento=documento, ordem=g.ordem, pagina=g.pagina, secao=g.secao[:255], texto=g.texto)
                    for g in gerados
                ]
            )
            with connection.cursor() as cursor:
                cursor.execute(SQL_TSVECTOR, [documento.id])
        aviso = _indexar_semantica(documento)
        if aviso:
            EtapaProcessamento.objects.create(
                documento=documento, etapa=StatusDocumento.INDEXANDO, situacao="aviso", mensagem=aviso
            )

        _concluir(documento, len(gerados))
    except FalhaExtracao as erro:
        _falhar(documento, str(erro))
    except Exception as erro:  # pragma: no cover - falha inesperada
        logger.exception("Falha ao processar documento %s", documento.id)
        _falhar(documento, f"Falha inesperada no processamento ({erro.__class__.__name__}).")
    return documento


def _indexar_semantica(documento: Documento) -> str:
    provedor = obter_provedor()
    trechos = list(documento.trechos.order_by("ordem"))
    try:
        for i in range(0, len(trechos), LOTE_EMBEDDING):
            lote = trechos[i : i + LOTE_EMBEDDING]
            vetores = provedor.embed([f"{documento.titulo}\n{t.secao}\n{t.texto}" for t in lote])
            for trecho, vetor in zip(lote, vetores, strict=True):
                trecho.embedding = vetor
            Trecho.objects.bulk_update(lote, ["embedding"])
        documento.indexacao_semantica = True
        documento.save(update_fields=["indexacao_semantica"])
        return ""
    except ProvedorIndisponivel:
        documento.indexacao_semantica = False
        documento.save(update_fields=["indexacao_semantica"])
        return (
            "Serviço de IA indisponível: documento indexado apenas para busca textual. "
            "Execute 'manage.py reindexar_semantica' quando o serviço voltar."
        )


def _concluir(documento: Documento, total_trechos: int) -> None:
    with transaction.atomic():
        documento.status = StatusDocumento.DISPONIVEL
        documento.disponibilizado_em = timezone.now()
        documento.mensagem_erro = ""
        documento.save(update_fields=["status", "disponibilizado_em", "mensagem_erro", "atualizado_em"])
        anterior = documento.versao_anterior
        if anterior and anterior.status == StatusDocumento.DISPONIVEL:
            anterior.status = StatusDocumento.ARQUIVADO
            anterior.save(update_fields=["status", "atualizado_em"])
    _etapa(documento, StatusDocumento.DISPONIVEL, mensagem=f"{total_trechos} trechos indexados.")
    registrar(
        None,
        "DOCUMENTO_PROCESSADO",
        usuario=documento.criado_por,
        objeto=documento,
        detalhes={"trechos": total_trechos, "semantica": documento.indexacao_semantica},
    )
    if documento.criado_por:
        notificar(
            documento.criado_por,
            "documento_disponivel",
            "Documento disponível para consulta",
            documento.titulo,
            link=f"/documentos/{documento.id}",
        )


def _falhar(documento: Documento, mensagem: str) -> None:
    documento.status = StatusDocumento.FALHA
    documento.mensagem_erro = mensagem
    documento.save(update_fields=["status", "mensagem_erro", "atualizado_em"])
    _etapa(documento, StatusDocumento.FALHA, situacao="erro", mensagem=mensagem)
    registrar(
        None,
        "DOCUMENTO_PROCESSADO",
        usuario=documento.criado_por,
        objeto=documento,
        resultado="FALHA",
        detalhes={"erro": mensagem[:200]},
    )
    if documento.criado_por:
        notificar(
            documento.criado_por,
            "documento_falha",
            "Falha no processamento",
            f"{documento.titulo}: {mensagem}",
            link="/importacao",
        )


def proximo_da_fila() -> Documento | None:
    with transaction.atomic():
        documento = (
            Documento.objects.select_for_update(skip_locked=True)
            .filter(status=StatusDocumento.RECEBIDO)
            .order_by("criado_em", "id")
            .first()
        )
        if documento:
            documento.status = StatusDocumento.EXTRAINDO
            documento.save(update_fields=["status"])
    return documento


def agendar(documento: Documento) -> None:
    """Instalação local: processa em thread após o commit. Servidor: worker `processar_fila`."""
    if not settings.NEXO_INGESTAO["PROCESSAR_IMEDIATAMENTE"]:
        return

    def _rodar():
        try:
            processar(Documento.objects.get(pk=documento.pk))
        finally:
            connection.close()

    transaction.on_commit(lambda: threading.Thread(target=_rodar, daemon=True).start())


def extensao_valida(nome: str) -> str | None:
    extensao = Path(nome).suffix.lower()
    return extensao if extensao in settings.NEXO_FORMATOS_ACEITOS else None
