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
        fields = ["id", "username", "nome", "email", "matricula", "setor", "perfis", "funcoes"]

    def get_setor(self, obj):
        if not obj.setor:
            return None
        return {"id": obj.setor_id, "nome": obj.setor.nome, "sigla": obj.setor.sigla}

    def get_perfis(self, obj):
        return [{"codigo": p.codigo, "nome": p.nome} for p in obj.perfis.all()]

    def get_funcoes(self, obj):
        return sorted(obj.funcoes())


class UsuarioAdminSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, required=False, allow_blank=False)
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
        ]
        read_only_fields = ["last_login", "date_joined"]

    def validate(self, attrs):
        senha = attrs.get("senha")
        if senha:
            validate_password(senha)
        return attrs

    def create(self, validated_data):
        senha = validated_data.pop("senha", None)
        perfis = validated_data.pop("perfis", [])
        usuario = Usuario(**validated_data)
        if senha:
            usuario.set_password(senha)
        else:
            usuario.set_unusable_password()
        usuario.save()
        usuario.perfis.set(perfis)
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop("senha", None)
        perfis = validated_data.pop("perfis", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if senha:
            instance.set_password(senha)
        instance.save()
        if perfis is not None:
            instance.perfis.set(perfis)
        return instance
