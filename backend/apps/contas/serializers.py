from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Funcao, Perfil, Usuario


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ["id", "codigo", "nome", "descricao", "funcoes"]

    def validate_funcoes(self, valor):
        validas = set(Funcao.values)
        invalidas = [f for f in valor if f not in validas]
        if invalidas:
            raise serializers.ValidationError(f"Funções inválidas: {', '.join(invalidas)}")
        return sorted(set(valor))


class UsuarioResumoSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="nome_completo", read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "nome", "username"]


class MeuUsuarioSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="nome_completo", read_only=True)
    setor = serializers.SerializerMethodField()
    perfis = serializers.SerializerMethodField()
    funcoes = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nome",
            "email",
            "matricula",
            "setor",
            "perfis",
            "funcoes",
            "trocar_senha",
            "pode_alterar_senha",
        ]

    def get_setor(self, obj):
        if not obj.setor:
            return None
        return {"id": obj.setor_id, "nome": obj.setor.nome, "sigla": obj.setor.sigla}

    def get_perfis(self, obj):
        return [{"codigo": p.codigo, "nome": p.nome} for p in obj.perfis.all()]

    def get_funcoes(self, obj):
        return sorted(obj.funcoes())

    trocar_senha = serializers.BooleanField(source="senha_temporaria", read_only=True)
    pode_alterar_senha = serializers.SerializerMethodField()

    def get_pode_alterar_senha(self, obj) -> bool:
        """Conta só com login Microsoft (sem senha local) troca a senha na própria Microsoft."""
        return obj.has_usable_password()


class UsuarioAdminSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, required=False, allow_blank=False)
    gerar_senha = serializers.BooleanField(write_only=True, required=False, default=False)
    enviar_link = serializers.BooleanField(write_only=True, required=False, default=False)  # ADR-027
    setor_nome = serializers.CharField(source="setor.nome", read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nome_exibicao",
            "first_name",
            "last_name",
            "email",
            "matricula",
            "setor",
            "setor_nome",
            "perfis",
            "is_active",
            "last_login",
            "date_joined",
            "senha",
            "gerar_senha",
            "enviar_link",
            "senha_temporaria",
            "senha_temporaria_expira_em",
            "tem_login_microsoft",
        ]
        read_only_fields = ["last_login", "date_joined", "senha_temporaria", "senha_temporaria_expira_em"]

    tem_login_microsoft = serializers.SerializerMethodField()

    def get_tem_login_microsoft(self, obj) -> bool:
        return bool(obj.id_externo)

    def validate(self, attrs):
        senha = attrs.get("senha")
        if sum(bool(x) for x in (senha, attrs.get("gerar_senha"), attrs.get("enviar_link"))) > 1:
            raise serializers.ValidationError(
                {"senha": "Escolha uma forma de acesso: link, senha gerada ou senha informada."}
            )
        if senha:
            validate_password(senha)
        return attrs

    def create(self, validated_data):
        validated_data.pop("gerar_senha", None)  # tratado na view (ADR-018)
        validated_data.pop("enviar_link", None)  # tratado na view (ADR-027)
        senha = validated_data.pop("senha", None)
        perfis = validated_data.pop("perfis", [])
        usuario = Usuario(**validated_data)
        if senha:
            usuario.set_password(senha)
            usuario.senha_temporaria = True  # a pessoa cria a própria senha no primeiro acesso (ADR-018)
        else:
            usuario.set_unusable_password()
        usuario.save()
        usuario.perfis.set(perfis)
        return usuario

    def update(self, instance, validated_data):
        validated_data.pop("gerar_senha", None)
        validated_data.pop("enviar_link", None)
        senha = validated_data.pop("senha", None)
        perfis = validated_data.pop("perfis", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if senha:
            instance.set_password(senha)
            # senha definida pelo administrador também é provisória: a pessoa cria a sua no próximo acesso
            instance.senha_temporaria = True
            instance.senha_temporaria_expira_em = None
        instance.save()
        if perfis is not None:
            instance.perfis.set(perfis)
        return instance
