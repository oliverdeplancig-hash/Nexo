import re

from rest_framework import serializers

from .models import FonteRegra, Regra, VersaoRegra


class FonteRegraSerializer(serializers.ModelSerializer):
    documento_titulo = serializers.CharField(source="documento.titulo", read_only=True)
    documento_vigencia = serializers.CharField(source="documento.vigencia", read_only=True)

    class Meta:
        model = FonteRegra
        fields = [
            "id",
            "documento",
            "documento_titulo",
            "documento_vigencia",
            "pagina",
            "secao",
            "trecho_citado",
            "ordem",
        ]


class RegraSerializer(serializers.ModelSerializer):
    fontes = FonteRegraSerializer(many=True, required=False)
    setor_responsavel_sigla = serializers.CharField(source="setor_responsavel.sigla", read_only=True, default=None)

    class Meta:
        model = Regra
        fields = [
            "id",
            "codigo",
            "titulo",
            "tipo",
            "frases_exemplo",
            "palavras_chave",
            "termos_obrigatorios",
            "termos_excludentes",
            "padroes_regex",
            "resposta",
            "etapas",
            "setor_responsavel",
            "setor_responsavel_sigla",
            "setores_alvo",
            "perfis_alvo",
            "prioridade",
            "status",
            "vigencia_inicio",
            "vigencia_fim",
            "versao",
            "publicada_em",
            "fontes",
            "atualizado_em",
        ]
        read_only_fields = ["status", "versao", "publicada_em"]

    def validate_padroes_regex(self, valor):
        for padrao in valor:
            if len(padrao) > 300:
                raise serializers.ValidationError("Expressão regular muito longa (máx. 300 caracteres).")
            try:
                re.compile(padrao)
            except re.error as erro:
                raise serializers.ValidationError(f"Expressão inválida '{padrao}': {erro}")
        return valor

    def validate_frases_exemplo(self, valor):
        if not [f for f in valor if str(f).strip()]:
            raise serializers.ValidationError("Informe ao menos uma frase de exemplo.")
        return [str(f).strip() for f in valor if str(f).strip()]

    def validate_etapas(self, valor):
        for etapa in valor:
            if not isinstance(etapa, dict) or not etapa.get("titulo"):
                raise serializers.ValidationError("Cada etapa precisa de um título.")
        return valor

    def _gravar_fontes(self, regra, fontes):
        if fontes is None:
            return
        regra.fontes.all().delete()
        for ordem, fonte in enumerate(fontes):
            fonte.pop("ordem", None)
            FonteRegra.objects.create(regra=regra, ordem=ordem, **fonte)

    def create(self, validated_data):
        fontes = validated_data.pop("fontes", [])
        setores = validated_data.pop("setores_alvo", [])
        perfis = validated_data.pop("perfis_alvo", [])
        regra = Regra.objects.create(**validated_data)
        regra.setores_alvo.set(setores)
        regra.perfis_alvo.set(perfis)
        self._gravar_fontes(regra, fontes)
        return regra

    def update(self, instance, validated_data):
        fontes = validated_data.pop("fontes", None)
        setores = validated_data.pop("setores_alvo", None)
        perfis = validated_data.pop("perfis_alvo", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if setores is not None:
            instance.setores_alvo.set(setores)
        if perfis is not None:
            instance.perfis_alvo.set(perfis)
        self._gravar_fontes(instance, fontes)
        return instance


class VersaoRegraSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersaoRegra
        fields = ["versao", "conteudo", "publicada_em", "publicada_por"]
