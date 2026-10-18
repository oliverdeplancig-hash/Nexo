from rest_framework import serializers

from apps.acesso.models import Acao
from apps.acesso.servico import decidir

from .models import Categoria, Colecao, Documento, Trecho


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nome", "descricao"]


class ColecaoSerializer(serializers.ModelSerializer):
    total_documentos = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Colecao
        fields = ["id", "nome", "descricao", "superior", "setor", "pessoal", "total_documentos", "atualizado_em"]


def _pode_ver_classificacao(usuario, documento, acoes) -> bool:
    return bool({Acao.EDITAR, Acao.ADMINISTRAR} & acoes or usuario.setor_id == documento.setor_responsavel_id)


class DocumentoListaSerializer(serializers.ModelSerializer):
    setor_responsavel = serializers.SerializerMethodField()
    categoria = serializers.CharField(source="categoria.nome", default=None, read_only=True)
    responsavel = serializers.SerializerMethodField()
    classificacao = serializers.SerializerMethodField()
    acoes_permitidas = serializers.SerializerMethodField()
    favorito = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = [
            "id",
            "titulo",
            "tipo_arquivo",
            "setor_responsavel",
            "categoria",
            "responsavel",
            "classificacao",
            "status",
            "versao",
            "data_documento",
            "numero_referencia",
            "atualizado_em",
            "acoes_permitidas",
            "favorito",
        ]

    def _acoes(self, obj) -> set[str]:
        cache = self.context.setdefault("_acoes", {})
        if obj.pk not in cache:
            cache[obj.pk] = decidir(self.context["request"].user, obj).acoes
        return cache[obj.pk]

    def get_setor_responsavel(self, obj):
        return {
            "id": obj.setor_responsavel_id,
            "sigla": obj.setor_responsavel.sigla,
            "nome": obj.setor_responsavel.nome,
        }

    def get_responsavel(self, obj):
        # Exibido apenas para quem pode editar ou é do setor responsável.
        usuario = self.context["request"].user
        if obj.responsavel and _pode_ver_classificacao(usuario, obj, self._acoes(obj)):
            return obj.responsavel.nome_completo
        return None

    def get_classificacao(self, obj):
        usuario = self.context["request"].user
        if _pode_ver_classificacao(usuario, obj, self._acoes(obj)):
            return obj.classificacao
        return None

    def get_acoes_permitidas(self, obj):
        return sorted(self._acoes(obj))

    def get_favorito(self, obj):
        favoritos = self.context.get("favoritos")
        if favoritos is None:
            return obj.favoritado_por.filter(usuario=self.context["request"].user).exists()
        return obj.pk in favoritos


class DocumentoDetalheSerializer(DocumentoListaSerializer):
    palavras_chave = serializers.ListField(child=serializers.CharField(), read_only=True)
    colecoes = ColecaoSerializer(many=True, read_only=True)

    class Meta(DocumentoListaSerializer.Meta):
        fields = DocumentoListaSerializer.Meta.fields + [
            "descricao",
            "palavras_chave",
            "nome_arquivo_original",
            "tamanho_bytes",
            "hash_sha256",
            "total_paginas",
            "disponibilizado_em",
            "criado_em",
            "colecoes",
            "indexacao_semantica",
            "paginas_ocr",
            "mensagem_erro",
        ]


class DocumentoEdicaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = [
            "titulo",
            "descricao",
            "categoria",
            "palavras_chave",
            "data_documento",
            "numero_referencia",
            "responsavel",
            "classificacao",
            "permite_download_geral",
            "colecoes",
        ]


class TrechoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trecho
        fields = ["id", "ordem", "pagina", "secao", "texto"]
