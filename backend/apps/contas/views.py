from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.auditoria.servico import registrar
from apps.comum.permissoes import exige_funcao

from . import entra
from .models import FUNCOES_CRITICAS, Funcao, Perfil, Usuario
from .serializers import (
    MeuUsuarioSerializer,
    PerfilSerializer,
    UsuarioAdminSerializer,
)


class LimiteLogin(AnonRateThrottle):
    scope = "login"  # NEXO_LIMITE_LOGIN (padrão 10/min por IP)


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LimiteLogin])
def entrar(request):
    if not settings.NEXO_LOGIN_LOCAL:
        return Response({"detail": "Use o login institucional para entrar no Nexo."}, status=status.HTTP_403_FORBIDDEN)
    usuario = authenticate(
        request,
        username=request.data.get("usuario", ""),
        password=request.data.get("senha", ""),
    )
    if usuario is None or not usuario.is_active:
        registrar(request, "LOGIN", resultado="FALHA", detalhes={"usuario": request.data.get("usuario", "")[:150]})
        return Response({"detail": "Usuário ou senha inválidos."}, status=status.HTTP_400_BAD_REQUEST)
    login(request, usuario)
    registrar(request, "LOGIN", usuario=usuario)
    return Response(MeuUsuarioSerializer(usuario).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def provedores(request):
    """Formas de entrada disponíveis, para a tela de login."""
    return Response(
        {
            "senha_local": settings.NEXO_LOGIN_LOCAL,
            "microsoft": {"ativo": entra.ativo(), "rotulo": settings.NEXO_ENTRA["ROTULO"]},
        }
    )


def _voltar_ao_login(codigo: str) -> HttpResponseRedirect:
    return HttpResponseRedirect("/entrar?" + urlencode({"erro": codigo}))


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([LimiteLogin])
def microsoft_iniciar(request):
    if not entra.ativo():
        return _voltar_ao_login("desativado")
    try:
        return HttpResponseRedirect(entra.iniciar(request, request.GET.get("destino", "/")))
    except entra.FalhaEntra as falha:
        registrar(request, "LOGIN", resultado="FALHA", detalhes={"metodo": "microsoft", "motivo": falha.codigo})
        return _voltar_ao_login(falha.codigo)


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([LimiteLogin])
def microsoft_retorno(request):
    if not entra.ativo():
        return _voltar_ao_login("desativado")
    try:
        usuario, destino = entra.concluir(request)
    except entra.FalhaEntra as falha:
        registrar(
            request,
            "LOGIN",
            resultado="FALHA",
            detalhes={"metodo": "microsoft", "motivo": falha.codigo, "detalhe": falha.detalhe[:300]},
        )
        return _voltar_ao_login(falha.codigo)
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    registrar(request, "LOGIN", usuario=usuario, detalhes={"metodo": "microsoft"})
    return HttpResponseRedirect(destino)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sair(request):
    registrar(request, "LOGOUT")
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def eu(request):
    return Response(MeuUsuarioSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def funcoes(request):
    return Response([{"valor": f.value, "rotulo": f.label, "critica": f in FUNCOES_CRITICAS} for f in Funcao])


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioAdminSerializer
    permission_classes = [exige_funcao(Funcao.ADMIN_USUARIOS)]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Usuario.objects.select_related("setor").prefetch_related("perfis").order_by("username")
        termo = self.request.query_params.get("q")
        if termo:
            qs = qs.filter(username__icontains=termo) | qs.filter(nome_exibicao__icontains=termo)
        setor = self.request.query_params.get("setor")
        if setor:
            qs = qs.filter(setor_id=setor)
        return qs

    def _verificar_perfis_criticos(self, serializer):
        """Atribuir perfil com função crítica exige `admin_permissoes`."""
        perfis = serializer.validated_data.get("perfis") or []
        criticos = [p for p in perfis if FUNCOES_CRITICAS & set(p.funcoes or [])]
        if criticos and not self.request.user.tem_funcao(Funcao.ADMIN_PERMISSOES):
            registrar(
                self.request, "FALHA_AUTORIZACAO", resultado="NEGADO", detalhes={"operacao": "atribuir_perfil_critico"}
            )
            raise PermissionDenied("Somente administradores de permissões podem atribuir perfis críticos.")

    def perform_create(self, serializer):
        self._verificar_perfis_criticos(serializer)
        usuario = serializer.save()
        registrar(self.request, "ADMIN_USUARIO", objeto=usuario, detalhes={"acao": "criar"})

    def perform_update(self, serializer):
        self._verificar_perfis_criticos(serializer)
        alterados = sorted(k for k in serializer.validated_data if k != "senha")
        if "senha" in serializer.validated_data:
            alterados.append("senha")
        usuario = serializer.save()
        registrar(self.request, "ADMIN_USUARIO", objeto=usuario, detalhes={"acao": "alterar", "campos": alterados})


class PerfilViewSet(viewsets.ModelViewSet):
    queryset = Perfil.objects.all()
    serializer_class = PerfilSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [exige_funcao(Funcao.ADMIN_USUARIOS, Funcao.ADMIN_PERMISSOES)()]
        return [exige_funcao(Funcao.ADMIN_PERMISSOES)()]

    def perform_create(self, serializer):
        perfil = serializer.save()
        registrar(
            self.request, "ADMIN_PERMISSAO", objeto=perfil, detalhes={"acao": "criar_perfil", "funcoes": perfil.funcoes}
        )

    def perform_update(self, serializer):
        perfil = serializer.save()
        registrar(
            self.request,
            "ADMIN_PERMISSAO",
            objeto=perfil,
            detalhes={"acao": "alterar_perfil", "funcoes": perfil.funcoes},
        )

    def perform_destroy(self, instance):
        registrar(self.request, "ADMIN_PERMISSAO", objeto=instance, detalhes={"acao": "excluir_perfil"})
        instance.delete()
