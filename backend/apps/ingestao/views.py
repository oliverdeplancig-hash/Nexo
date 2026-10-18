import hashlib
import json

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.acesso.models import Acao, AutorizacaoDocumento, Classificacao
from apps.acesso.servico import decidir, documentos_visiveis
from apps.auditoria.servico import registrar
from apps.comum.permissoes import exige_funcao
from apps.contas.models import Funcao
from apps.documentos.models import Categoria, Documento, StatusDocumento
from apps.organizacao.models import Setor

from .extratores import FalhaExtracao, verificar_assinatura
from .models import EtapaProcessamento
from .pipeline import agendar, extensao_valida


def _lista(request, campo) -> list[str]:
    valores = request.data.getlist(campo) if hasattr(request.data, "getlist") else request.data.get(campo, [])
    saida = []
    for v in valores or []:
        saida.extend(p.strip() for p in str(v).split(",") if p.strip())
    return saida


def _criar_documento(request, arquivo, metadados: dict, versao_anterior: Documento | None = None) -> dict:
    extensao = extensao_valida(arquivo.name)
    if not extensao:
        return {"arquivo": arquivo.name, "erro": "Formato não suportado. Use PDF, DOCX, TXT, MD ou HTML."}
    if arquivo.size > settings.NEXO_UPLOAD_MAX_MB * 1024 * 1024:
        return {"arquivo": arquivo.name, "erro": f"Arquivo acima de {settings.NEXO_UPLOAD_MAX_MB} MB."}
    cabecalho = arquivo.read(8)
    arquivo.seek(0)
    try:
        verificar_assinatura(cabecalho, extensao)
    except FalhaExtracao as erro:
        return {"arquivo": arquivo.name, "erro": str(erro)}

    sha = hashlib.sha256()
    for parte in arquivo.chunks():
        sha.update(parte)
    arquivo.seek(0)
    hash_hex = sha.hexdigest()
    # Só avisa sobre duplicata visível ao usuário (não revela documentos restritos).
    duplicado = (
        documentos_visiveis(request.user).filter(hash_sha256=hash_hex).exclude(status=StatusDocumento.ARQUIVADO).first()
    )

    titulo = metadados["titulo"] or arquivo.name.rsplit(".", 1)[0][:300]
    with transaction.atomic():
        documento = Documento(
            titulo=titulo,
            descricao=metadados["descricao"],
            categoria=metadados["categoria"],
            palavras_chave=metadados["palavras_chave"],
            data_documento=metadados["data_documento"],
            numero_referencia=metadados["numero_referencia"],
            setor_responsavel=metadados["setor"],
            responsavel_id=metadados["responsavel"] or request.user.id,
            criado_por=request.user,
            classificacao=metadados["classificacao"],
            permite_download_geral=metadados["permite_download_geral"],
            nome_arquivo_original=arquivo.name[:255],
            tipo_arquivo=extensao.lstrip("."),
            tamanho_bytes=arquivo.size,
            hash_sha256=hash_hex,
            versao=(versao_anterior.versao + 1) if versao_anterior else 1,
            versao_anterior=versao_anterior,
        )
        documento.arquivo.save(arquivo.name, arquivo, save=False)
        documento.save()
        if metadados["colecoes"]:
            from apps.documentos.colecoes import gerenciaveis

            documento.colecoes.set(gerenciaveis(request.user, metadados["colecoes"]))
        acoes = [Acao.BAIXAR] if metadados["autorizados_baixam"] else [Acao.VISUALIZAR]
        for setor_id in metadados["setores_autorizados"]:
            AutorizacaoDocumento.objects.create(
                documento=documento, setor_id=setor_id, acoes=acoes, concedido_por=request.user
            )
        for perfil_id in metadados["perfis_autorizados"]:
            AutorizacaoDocumento.objects.create(
                documento=documento, perfil_id=perfil_id, acoes=acoes, concedido_por=request.user
            )
        if versao_anterior:  # a nova versão herda as autorizações explícitas
            for aut in versao_anterior.autorizacoes.all():
                AutorizacaoDocumento.objects.create(
                    documento=documento,
                    usuario=aut.usuario,
                    setor=aut.setor,
                    perfil=aut.perfil,
                    acoes=aut.acoes,
                    valido_ate=aut.valido_ate,
                    concedido_por=request.user,
                    motivo="herdada da versão anterior",
                )
        EtapaProcessamento.objects.create(documento=documento, etapa=StatusDocumento.RECEBIDO, situacao="ok")
        registrar(
            request,
            "DOCUMENTO_INCLUIDO",
            objeto=documento,
            detalhes={"versao": documento.versao, "classificacao": documento.classificacao},
        )
        agendar(documento)
    resultado = {"arquivo": arquivo.name, "id": documento.id, "status": documento.status}
    if duplicado:
        resultado["aviso"] = "Já existe um documento com conteúdo idêntico no repositório."
    return resultado


def _metadados(request) -> dict:
    d = request.data
    setor_id = d.get("setor_responsavel") or request.user.setor_id
    if not setor_id:
        raise ValidationError({"setor_responsavel": "Informe o setor responsável."})
    setor = get_object_or_404(Setor, pk=setor_id, ativo=True)
    classificacao = d.get("classificacao") or Classificacao.SETOR
    if classificacao not in Classificacao.values:
        raise ValidationError({"classificacao": "Classificação inválida."})
    categoria = Categoria.objects.filter(pk=d.get("categoria")).first() if d.get("categoria") else None
    data_documento = parse_date(d.get("data_documento") or "") if d.get("data_documento") else None
    palavras = d.get("palavras_chave") or ""
    try:
        palavras_lista = (
            json.loads(palavras)
            if palavras.strip().startswith("[")
            else [p.strip() for p in palavras.split(",") if p.strip()]
        )
    except (ValueError, AttributeError):
        palavras_lista = []
    return {
        "titulo": (d.get("titulo") or "").strip()[:300],
        "descricao": d.get("descricao") or "",
        "categoria": categoria,
        "palavras_chave": palavras_lista[:20],
        "data_documento": data_documento,
        "numero_referencia": (d.get("numero_referencia") or "")[:120],
        "setor": setor,
        "responsavel": d.get("responsavel") or None,
        "classificacao": classificacao,
        "permite_download_geral": str(d.get("permite_download_geral", "")).lower() in ("1", "true", "sim"),
        "autorizados_baixam": str(d.get("autorizados_baixam", "")).lower() in ("1", "true", "sim"),
        "setores_autorizados": _lista(request, "setores_autorizados"),
        "perfis_autorizados": _lista(request, "perfis_autorizados"),
        "colecoes": _lista(request, "colecoes"),
    }


@api_view(["POST"])
@permission_classes([exige_funcao(Funcao.IMPORTAR_DOCUMENTOS)])
@parser_classes([MultiPartParser, FormParser])
def importar(request):
    """Tela 07 — recebe um ou vários arquivos com os mesmos metadados."""
    arquivos = request.FILES.getlist("arquivos")
    if not arquivos:
        raise ValidationError({"arquivos": "Selecione ao menos um arquivo."})
    metadados = _metadados(request)
    if len(arquivos) > 1:
        metadados["titulo"] = ""  # vários arquivos: título vem do nome de cada um
    resultados = [_criar_documento(request, a, metadados) for a in arquivos]
    codigo = status.HTTP_201_CREATED if any("id" in r for r in resultados) else status.HTTP_400_BAD_REQUEST
    return Response({"resultados": resultados}, status=codigo)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def nova_versao(request, documento_id):
    anterior = get_object_or_404(Documento, pk=documento_id)
    decisao = decidir(request.user, anterior)
    if not decisao.permite(Acao.CONSULTAR):
        raise Http404
    if not decisao.permite(Acao.EDITAR):
        raise PermissionDenied("Você não pode publicar nova versão deste documento.")
    arquivo = request.FILES.get("arquivo")
    if not arquivo:
        raise ValidationError({"arquivo": "Selecione o arquivo da nova versão."})
    metadados = {
        "titulo": anterior.titulo,
        "descricao": request.data.get("descricao") or anterior.descricao,
        "categoria": anterior.categoria,
        "palavras_chave": anterior.palavras_chave,
        "data_documento": parse_date(request.data.get("data_documento") or "") or anterior.data_documento,
        "numero_referencia": anterior.numero_referencia,
        "setor": anterior.setor_responsavel,
        "responsavel": anterior.responsavel_id,
        "classificacao": anterior.classificacao,
        "permite_download_geral": anterior.permite_download_geral,
        "autorizados_baixam": False,
        "setores_autorizados": [],
        "perfis_autorizados": [],
        "colecoes": list(anterior.colecoes.values_list("id", flat=True)),
    }
    resultado = _criar_documento(request, arquivo, metadados, versao_anterior=anterior)
    return Response(resultado, status=status.HTTP_201_CREATED if "id" in resultado else status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def fila(request):
    """Documentos cadastrados pelo usuário e o andamento de cada um."""
    documentos = Documento.objects.filter(criado_por=request.user).order_by("-criado_em")[:50]
    etapas = EtapaProcessamento.objects.filter(documento__in=documentos)
    por_doc: dict[int, list] = {}
    for e in etapas:
        por_doc.setdefault(e.documento_id, []).append(
            {"etapa": e.etapa, "situacao": e.situacao, "mensagem": e.mensagem, "ocorrido_em": e.ocorrido_em}
        )
    return Response(
        [
            {
                "id": d.id,
                "titulo": d.titulo,
                "arquivo": d.nome_arquivo_original,
                "tamanho_bytes": d.tamanho_bytes,
                "status": d.status,
                "mensagem_erro": d.mensagem_erro,
                "criado_em": d.criado_em,
                "etapas": por_doc.get(d.id, []),
            }
            for d in documentos
        ]
    )


@api_view(["POST"])
def reprocessar(request, documento_id):
    documento = get_object_or_404(Documento, pk=documento_id)
    if not decidir(request.user, documento).permite(Acao.EDITAR):
        raise Http404
    if documento.status not in (StatusDocumento.FALHA, StatusDocumento.DISPONIVEL):
        raise ValidationError({"status": "O documento já está em processamento."})
    documento.status = StatusDocumento.RECEBIDO
    documento.mensagem_erro = ""
    documento.save(update_fields=["status", "mensagem_erro", "atualizado_em"])
    EtapaProcessamento.objects.create(
        documento=documento, etapa=StatusDocumento.RECEBIDO, situacao="ok", mensagem="Reprocessamento solicitado."
    )
    agendar(documento)
    return Response({"id": documento.id, "status": documento.status})
