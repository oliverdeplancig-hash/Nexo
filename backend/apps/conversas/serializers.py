from rest_framework import serializers

from apps.acesso.models import Acao
from apps.acesso.servico import decidir

from .models import Conversa, Mensagem


def _usuario(contexto):
    if contexto.get("usuario") is not None:
        return contexto["usuario"]
    return contexto["request"].user


class MensagemSerializer(serializers.ModelSerializer):
    fontes = serializers.SerializerMethodField()
    avaliacao = serializers.SerializerMethodField()

    class Meta:
        model = Mensagem
        fields = [
            "id",
            "papel",
            "conteudo",
            "origem",
            "confianca",
            "etapas",
            "setor",
            "setores_sugeridos",
            "sugestoes",
            "fontes",
            "rastro",
            "interrompida",
            "duracao_ms",
            "criada_em",
            "avaliacao",
        ]

    def get_avaliacao(self, obj):
        if obj.papel != Mensagem.Papel.ASSISTENTE:
            return None
        from .lacunas import serializar_avaliacao

        return serializar_avaliacao(obj)

    def get_fontes(self, obj):
        """Permissões são reavaliadas a cada leitura: se o acesso a um documento
        foi revogado depois da conversa, a fonte deixa de aparecer no histórico."""
        if not obj.fontes:
            return []
        from apps.documentos.models import Documento

        usuario = _usuario(self.context)
        documentos = Documento.objects.in_bulk({f["documento_id"] for f in obj.fontes})
        saida = []
        for fonte in obj.fontes:
            doc = documentos.get(fonte["documento_id"])
            if doc is None:
                continue
            decisao = decidir(usuario, doc)
            if not decisao.permite(Acao.CONSULTAR):
                continue
            saida.append({**fonte, "pode_abrir": decisao.permite(Acao.VISUALIZAR)})
        return saida


class ConversaSerializer(serializers.ModelSerializer):
    documento_contexto_titulo = serializers.SerializerMethodField()
    ultima_mensagem_em = serializers.DateTimeField(source="atualizada_em", read_only=True)
    memoria = serializers.SerializerMethodField()

    class Meta:
        model = Conversa
        fields = [
            "id",
            "titulo",
            "documento_contexto",
            "documento_contexto_titulo",
            "arquivada",
            "criada_em",
            "ultima_mensagem_em",
            "memoria",
        ]
        read_only_fields = ["documento_contexto", "criada_em"]

    def get_memoria(self, obj) -> dict:
        from .memoria import resumo_publico

        return resumo_publico(obj)

    def get_documento_contexto_titulo(self, obj):
        doc = obj.documento_contexto
        if doc is None:
            return None
        if not decidir(_usuario(self.context), doc).permite(Acao.CONSULTAR):
            return None
        return doc.titulo
