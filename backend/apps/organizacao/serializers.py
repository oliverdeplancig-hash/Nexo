from rest_framework import serializers

from .models import Setor


class SetorSerializer(serializers.ModelSerializer):
    canal_contato = serializers.SerializerMethodField()

    class Meta:
        model = Setor
        fields = [
            "id",
            "nome",
            "sigla",
            "setor_superior",
            "descricao",
            "competencias",
            "tipos_demanda",
            "servicos",
            "procedimentos_relacionados",
            "canal_contato",
            "horario_atendimento",
            "orientacao_acesso",
            "palavras_chave",
            "contato_visivel_para_todos",
            "ativo",
            "atualizado_em",
        ]

    def get_canal_contato(self, obj):
        usuario = self.context["request"].user
        if obj.contato_visivel_para_todos or usuario.setor_id == obj.id:
            return obj.canal_contato
        return None


class SetorEdicaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setor
        exclude = ["criado_em", "atualizado_em"]
