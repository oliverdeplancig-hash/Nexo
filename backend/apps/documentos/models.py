import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone
from pgvector.django import HnswIndex, VectorField

from apps.acesso.models import Classificacao
from apps.comum.modelos import ModeloComDatas


def armazenamento_protegido():
    """Diretório fora da raiz web; arquivos só saem pela view autorizada."""
    return FileSystemStorage(location=settings.NEXO_ARMAZENAMENTO_DIR, base_url=None)


def caminho_arquivo(instancia, nome_original):
    extensao = Path(nome_original).suffix.lower()
    agora = timezone.now()
    return f"documentos/{agora:%Y/%m}/{uuid.uuid4().hex}{extensao}"


class StatusDocumento(models.TextChoices):
    RECEBIDO = "recebido", "Arquivo recebido"
    EXTRAINDO = "extraindo", "Extração de conteúdo"
    METADADOS = "metadados", "Identificação de metadados"
    INDEXANDO = "indexando", "Indexação para pesquisa"
    DISPONIVEL = "disponivel", "Disponível para consulta"
    FALHA = "falha", "Falha no processamento"
    ARQUIVADO = "arquivado", "Arquivado"


class Vigencia(models.TextChoices):
    VIGENTE = "vigente", "Vigente"
    REVOGADO = "revogado", "Revogado"


class Categoria(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Colecao(ModeloComDatas):
    """Pasta ou coleção. Agrupa documentos sem alterar suas permissões."""

    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    superior = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="subcolecoes")
    setor = models.ForeignKey("organizacao.Setor", null=True, blank=True, on_delete=models.PROTECT)
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    pessoal = models.BooleanField(default=False, help_text="Visível apenas para quem criou.")

    class Meta:
        ordering = ["nome"]
        verbose_name = "coleção"
        verbose_name_plural = "coleções"

    def __str__(self):
        return self.nome


class Documento(ModeloComDatas):
    titulo = models.CharField("título", max_length=300)
    descricao = models.TextField("descrição", blank=True)
    categoria = models.ForeignKey(Categoria, null=True, blank=True, on_delete=models.SET_NULL)
    palavras_chave = models.JSONField(default=list, blank=True)
    data_documento = models.DateField(null=True, blank=True)
    numero_referencia = models.CharField("número ou código de referência", max_length=120, blank=True)

    arquivo = models.FileField(storage=armazenamento_protegido, upload_to=caminho_arquivo, max_length=255)
    nome_arquivo_original = models.CharField(max_length=255)
    tipo_arquivo = models.CharField(max_length=10)
    tamanho_bytes = models.BigIntegerField(default=0)
    hash_sha256 = models.CharField(max_length=64, db_index=True)
    total_paginas = models.PositiveIntegerField(null=True, blank=True)

    setor_responsavel = models.ForeignKey("organizacao.Setor", on_delete=models.PROTECT, related_name="documentos")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documentos_mantidos",
        verbose_name="responsável pela manutenção",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="documentos_cadastrados"
    )

    classificacao = models.CharField(max_length=20, choices=Classificacao.choices, default=Classificacao.SETOR)
    permite_download_geral = models.BooleanField(default=False)

    versao = models.PositiveIntegerField(default=1)
    versao_anterior = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="versao_seguinte"
    )
    colecoes = models.ManyToManyField(Colecao, blank=True, related_name="documentos")

    status = models.CharField(max_length=20, choices=StatusDocumento.choices, default=StatusDocumento.RECEBIDO)
    mensagem_erro = models.TextField(blank=True)
    indexacao_semantica = models.BooleanField(default=False)
    paginas_ocr = models.PositiveIntegerField(
        "páginas lidas por OCR", default=0, help_text="Texto obtido por reconhecimento óptico; pode conter erros."
    )
    disponibilizado_em = models.DateTimeField(null=True, blank=True)

    # Vigência e revisão (ADR-015)
    vigencia = models.CharField("vigência", max_length=12, choices=Vigencia.choices, default=Vigencia.VIGENTE)
    revogado_em = models.DateField("revogado em", null=True, blank=True)
    motivo_revogacao = models.CharField("motivo da revogação", max_length=500, blank=True)
    substituido_por = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="substitui",
        verbose_name="substituído por",
    )
    revisar_em = models.DateField("próxima revisão", null=True, blank=True)
    revisado_em = models.DateField("última revisão", null=True, blank=True)
    revisao_avisada_em = models.DateField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-atualizado_em"]
        indexes = [
            models.Index(fields=["status", "classificacao", "setor_responsavel"]),
            models.Index(fields=["titulo"]),
            models.Index(fields=["vigencia", "revisar_em"]),
        ]

    def __str__(self):
        return self.titulo


class Trecho(models.Model):
    """Fragmento indexado de um documento (unidade de busca e de citação)."""

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="trechos")
    ordem = models.PositiveIntegerField()
    pagina = models.PositiveIntegerField(null=True, blank=True)
    secao = models.CharField(max_length=255, blank=True)
    texto = models.TextField()
    busca = SearchVectorField(null=True)
    embedding = VectorField(dimensions=settings.NEXO_IA["DIMENSAO_EMBEDDING"], null=True, blank=True)

    class Meta:
        ordering = ["documento", "ordem"]
        unique_together = [("documento", "ordem")]
        indexes = [
            GinIndex(fields=["busca"], name="trecho_busca_gin"),
            HnswIndex(
                name="trecho_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.documento_id}#{self.ordem}"


class Favorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoritos")
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="favoritado_por")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("usuario", "documento")]


class AcessoRecente(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acessos_recentes")
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="+")
    acessado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("usuario", "documento")]
        ordering = ["-acessado_em"]
