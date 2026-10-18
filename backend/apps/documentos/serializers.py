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
    pode_editar = serializers.SerializerMethodField()
    criada_por_nome = serializers.SerializerMethodField()

    class Meta:
        model = Colecao
        fields = [
            "id",
            "nome",
            "descricao",
            "superior",
            "setor",
            "pessoal",
            "total_documentos",
            "pode_editar",
            "criada_por_nome",
            "atualizado_em",
        ]

    def _usuario(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def get_pode_editar(self, obj) -> bool:
        from .colecoes import pode_gerir

        return pode_gerir(self._usuario(), obj)

    def get_criada_por_nome(self, obj) -> str:
        return obj.criada_por.nome_completo if obj.criada_por_id and obj.criada_por else ""

    def validate_nome(self, valor):
        valor = (valor or "").strip()
        if not valor:
            raise serializers.ValidationError("Informe o nome da coleção.")
        return valor

    def validate_superior(self, superior):
        if superior is None:
            return None
        from .colecoes import visiveis

        if not visiveis(self._usuario()).filter(pk=superior.pk).exists():
            raise serializers.ValidationError("Coleção superior não encontrada.")
        atual = self.instance
        no = superior
        while no is not None:  # impede ciclos (A dentro de B dentro de A)
            if atual is not None and no.pk == atual.pk:
                raise serializers.ValidationError("Uma coleção não pode ficar dentro dela mesma.")
            no = no.superior
        return superior

    def validate(self, dados):
        # Pessoal/institucional é definido na criação e não muda depois.
        if self.instance is not None:
            dados.pop("pessoal", None)
        return dados


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
    colecoes = serializers.SerializerMethodField()

    def get_colecoes(self, obj):
        """Só as coleções que a pessoa pode ver (coleções pessoais de outras pessoas não aparecem)."""
        from .colecoes import filtro_visiveis

        usuario = self.context["request"].user
        qs = obj.colecoes.filter(filtro_visiveis(usuario)).select_related("criada_por").order_by("nome")
        return ColecaoSerializer(qs, many=True, context=self.context).data

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

    def update(self, instance, dados):
        # Coleções: só mexe nas que a pessoa organiza (ver apps/documentos/colecoes.py).
        colecoes = dados.pop("colecoes", None)
        instance = super().update(instance, dados)
        if colecoes is not None:
            from .colecoes import substituir_do_documento

            substituir_do_documento(self.context["request"].user, instance, [c.pk for c in colecoes])
        return instance


class TrechoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trecho
        fields = ["id", "ordem", "pagina", "secao", "texto"]
