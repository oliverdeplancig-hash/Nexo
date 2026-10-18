"""Permissões DRF para funções administrativas (não documentais).

O acesso a documentos é decidido exclusivamente por `apps.acesso.servico`.
"""

from rest_framework.permissions import BasePermission


def exige_funcao(*funcoes: str) -> type[BasePermission]:
    class _TemFuncao(BasePermission):
        message = "Seu perfil não possui autorização para esta operação."

        def has_permission(self, request, view):
            usuario = request.user
            return bool(
                usuario
                and usuario.is_authenticated
                and usuario.is_active
                and any(usuario.tem_funcao(f) for f in funcoes)
            )

    _TemFuncao.__name__ = "TemFuncao_" + "_".join(funcoes)
    return _TemFuncao
