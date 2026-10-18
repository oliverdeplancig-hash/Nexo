import mimetypes

from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.acesso.models import Acao, AutorizacaoDocumento
from apps.acesso.servico import decidir, documentos_visiveis
from apps.auditoria.servico import registrar
from apps.contas.models import Funcao

from . import colecoes as colecoes_regras
from .models import AcessoRecente, Categoria, Favorito
from .serializers import (
    CategoriaSerializer,
    ColecaoSerializer,
    DocumentoDetalheSerializer,
    DocumentoEdicaoSerializer,
    DocumentoListaSerializer,
    TrechoSerializer,
)

ORDENACOES = {
    "titulo": "titulo",
    "-titulo": "-titulo",
    "atualizacao": "atualizado_em",
    "-atualizacao": "-atualizado_em",
    "tipo": "tipo_arquivo",
    "-tipo": "-tipo_arquivo",
    "setor": "setor_responsavel__sigla",
    "-setor": "-setor_responsavel__sigla",
}


class DocumentoViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Repositório documental. Toda consulta parte de `documentos_visiveis`."""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DocumentoDetalheSerializer
        if self.action in ("update", "partial_update"):
            return DocumentoEdicaoSerializer
        return DocumentoListaSerializer

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        if self.request.user.is_authenticated:
            contexto["favoritos"] = set(
                Favorito.objects.filter(usuario=self.request.user).values_list("documento_id", flat=True)
            )
        return contexto

    def get_queryset(self):
        usuario = self.request.user
        qs = documentos_visiveis(usuario).select_related("setor_responsavel", "categoria", "responsavel")
        p = self.request.query_params
        aba = p.get("aba", "todos")
        if aba == "meus":
            qs = qs.filter(Q(responsavel=usuario) | Q(criado_por=usuario))
        elif aba == "favoritos":
            qs = qs.filter(favoritado_por__usuario=usuario)
        elif aba == "recentes":
            qs = qs.filter(id__in=AcessoRecente.objects.filter(usuario=usuario).values("documento_id")[:50])
        elif aba == "compartilhados":
            qs = qs.filter(
                autorizacoes__usuario=usuario,
            ).filter(Q(autorizacoes__valido_ate__isnull=True) | Q(autorizacoes__valido_ate__gt=timezone.now()))
        if p.get("q"):
            qs = qs.filter(Q(titulo__icontains=p["q"]) | Q(numero_referencia__icontains=p["q"]))
        if p.get("tipo"):
            qs = qs.filter(tipo_arquivo__in=p["tipo"].split(","))
        if p.get("setor"):
            qs = qs.filter(setor_responsavel_id__in=p["setor"].split(","))
        if p.get("categoria"):
            qs = qs.filter(categoria_id__in=p["categoria"].split(","))
        if p.get("colecao"):
            # Coleção pessoal de outra pessoa não filtra nada (não revela o que há nela).
            colecao = (
                colecoes_regras.visiveis(self.request.user).filter(pk=p["colecao"]).first()
                if str(p["colecao"]).isdigit()
                else None
            )
            qs = qs.filter(colecoes=colecao) if colecao else qs.none()
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("de") and parse_date(p["de"]):
            qs = qs.filter(atualizado_em__date__gte=parse_date(p["de"]))
        if p.get("ate") and parse_date(p["ate"]):
            qs = qs.filter(atualizado_em__date__lte=parse_date(p["ate"]))
        ordem = ORDENACOES.get(p.get("ordem", "-atualizacao"), "-atualizado_em")
        return qs.order_by(ordem, "id")

    def get_object(self):
        documento = super().get_object()
        # 404 (e não 403) quando não há acesso: não revelamos a existência do documento.
        if not decidir(self.request.user, documento).permite(Acao.VISUALIZAR):
            raise Http404
        return documento

    def retrieve(self, request, *args, **kwargs):
        documento = self.get_object()
        AcessoRecente.objects.update_or_create(
            usuario=request.user, documento=documento, defaults={"acessado_em": timezone.now()}
        )
        registrar(request, "DOCUMENTO_ABERTO", objeto=documento)
        return Response(self.get_serializer(documento).data)

    def perform_update(self, serializer):
        documento = serializer.instance
        decisao = decidir(self.request.user, documento)
        if not decisao.permite(Acao.EDITAR):
            registrar(
                self.request, "FALHA_AUTORIZACAO", objeto=documento, resultado="NEGADO", detalhes={"operacao": "editar"}
            )
            raise PermissionDenied("Você não pode editar este documento.")
        campos_acesso = {"classificacao", "permite_download_geral"} & set(serializer.validated_data)
        if campos_acesso and not decisao.permite(Acao.ADMINISTRAR):
            raise PermissionDenied("Alterar a classificação exige permissão de administrar o documento.")
        serializer.save()
        registrar(
            self.request,
            "DOCUMENTO_ALTERADO",
            objeto=documento,
            detalhes={"campos": sorted(serializer.validated_data)},
        )

    def destroy(self, request, *args, **kwargs):
        """Arquiva (não apaga) o documento."""
        documento = self.get_object()
        if not decidir(request.user, documento).permite(Acao.ADMINISTRAR):
            raise PermissionDenied("Você não pode arquivar este documento.")
        from .models import StatusDocumento

        documento.status = StatusDocumento.ARQUIVADO
        documento.save(update_fields=["status", "atualizado_em"])
        registrar(request, "DOCUMENTO_ARQUIVADO", objeto=documento)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def arquivo(self, request, pk=None):
        documento = self.get_object()
        baixar = request.query_params.get("download") == "1"
        if baixar and not decidir(request.user, documento).permite(Acao.BAIXAR):
            registrar(
                request, "FALHA_AUTORIZACAO", objeto=documento, resultado="NEGADO", detalhes={"operacao": "baixar"}
            )
            raise PermissionDenied("Seu perfil não permite baixar este documento.")
        registrar(request, "DOCUMENTO_BAIXADO" if baixar else "DOCUMENTO_VISUALIZADO", objeto=documento)
        tipo, _ = mimetypes.guess_type(documento.nome_arquivo_original)
        resposta = FileResponse(
            documento.arquivo.open("rb"),
            as_attachment=baixar,
            filename=documento.nome_arquivo_original,
            content_type=tipo or "application/octet-stream",
        )
        resposta["Cache-Control"] = "private, no-store"
        if documento.tipo_arquivo in ("html", "htm"):
            # HTML enviado por usuários nunca executa scripts na origem do Nexo.
            # (Não se aplica a PDF: navegadores bloqueiam o visualizador de PDF em sandbox.)
            resposta["Content-Security-Policy"] = "sandbox"
        return resposta

    @action(detail=True, methods=["get"])
    def conteudo(self, request, pk=None):
        documento = self.get_object()
        trechos = documento.trechos.all()
        if request.query_params.get("pagina"):
            trechos = trechos.filter(pagina=request.query_params["pagina"])
        return Response(TrechoSerializer(trechos[:200], many=True).data)

    @action(detail=True, methods=["post", "delete"])
    def favorito(self, request, pk=None):
        documento = self.get_object()
        if request.method == "POST":
            Favorito.objects.get_or_create(usuario=request.user, documento=documento)
            return Response({"favorito": True})
        Favorito.objects.filter(usuario=request.user, documento=documento).delete()
        return Response({"favorito": False})

    @action(detail=True, methods=["get"])
    def referencia(self, request, pk=None):
        documento = self.get_object()
        partes = [documento.titulo]
        if documento.numero_referencia:
            partes.append(documento.numero_referencia)
        partes.append(documento.setor_responsavel.sigla)
        if documento.data_documento:
            partes.append(documento.data_documento.strftime("%d/%m/%Y"))
        partes.append(f"versão {documento.versao}")
        return Response({"referencia": ". ".join(partes) + "."})

    @action(detail=True, methods=["post"])
    def compartilhar(self, request, pk=None):
        documento = self.get_object()
        decisao = decidir(request.user, documento)
        if not decisao.permite(Acao.COMPARTILHAR):
            registrar(
                request,
                "FALHA_AUTORIZACAO",
                objeto=documento,
                resultado="NEGADO",
                detalhes={"operacao": "compartilhar"},
            )
            raise PermissionDenied("Você não pode compartilhar este documento.")
        acoes = set(request.data.get("acoes") or [Acao.VISUALIZAR])
        # Ninguém concede o que não tem; "administrar" só por quem administra permissões.
        if not acoes <= decisao.acoes:
            raise PermissionDenied("Você só pode conceder ações que você mesmo possui.")
        if Acao.ADMINISTRAR in acoes and not request.user.tem_funcao(Funcao.ADMIN_PERMISSOES):
            raise PermissionDenied("Conceder administração exige o perfil de administração de permissões.")
        autorizacao = AutorizacaoDocumento(
            documento=documento,
            usuario_id=request.data.get("usuario"),
            setor_id=request.data.get("setor"),
            perfil_id=request.data.get("perfil"),
            acoes=sorted(acoes),
            valido_ate=request.data.get("valido_ate") or None,
            concedido_por=request.user,
            motivo=(request.data.get("motivo") or "")[:255],
        )
        try:
            autorizacao.save()
        except Exception as erro:  # ValidationError do modelo
            return Response({"detail": str(erro)}, status=status.HTTP_400_BAD_REQUEST)
        registrar(
            request,
            "PERMISSAO_CONCEDIDA",
            objeto=documento,
            detalhes={"destinatario": autorizacao.destinatario, "acoes": autorizacao.acoes},
        )
        return Response({"id": autorizacao.id}, status=status.HTTP_201_CREATED)


class ColecaoViewSet(viewsets.ModelViewSet):
    """Pastas e coleções. Regras em apps/documentos/colecoes.py."""

    serializer_class = ColecaoSerializer

    def get_queryset(self):
        usuario = self.request.user
        visiveis = documentos_visiveis(usuario).values("id")
        return (
            colecoes_regras.visiveis(usuario)
            .select_related("criada_por")
            .annotate(total_documentos=Count("documentos", filter=Q(documentos__id__in=visiveis), distinct=True))
            .order_by("nome")
        )

    def _exigir_gestao(self, colecao):
        if not colecoes_regras.pode_gerir(self.request.user, colecao):
            if colecao.pessoal:
                raise PermissionDenied("Só quem criou pode alterar esta coleção pessoal.")
            raise PermissionDenied("Seu perfil não pode alterar coleções institucionais.")

    def perform_create(self, serializer):
        pessoal = serializer.validated_data.get("pessoal", False)
        if not pessoal and not self.request.user.tem_funcao(Funcao.GERIR_COLECOES):
            raise PermissionDenied("Você pode criar apenas coleções pessoais.")
        serializer.save(criada_por=self.request.user)

    def perform_update(self, serializer):
        self._exigir_gestao(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        # Os documentos não são apagados: só deixam de fazer parte da coleção (e das subcoleções).
        self._exigir_gestao(instance)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="documentos")
    def adicionar_documentos(self, request, pk=None):
        """{"documentos": [ids]} — inclui só documentos que a pessoa pode consultar."""
        colecao = self.get_object()
        self._exigir_gestao(colecao)
        ids = request.data.get("documentos") or []
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            return Response({"detail": "Informe a lista de documentos."}, status=status.HTTP_400_BAD_REQUEST)
        permitidos = list(documentos_visiveis(request.user).filter(id__in=ids).values_list("id", flat=True))
        colecao.documentos.add(*permitidos)
        colecao.save(update_fields=["atualizado_em"])
        return Response({"adicionados": len(permitidos), "ignorados": len(set(ids)) - len(permitidos)})

    @action(detail=True, methods=["delete"], url_path=r"documentos/(?P<documento_id>\d+)")
    def remover_documento(self, request, pk=None, documento_id=None):
        colecao = self.get_object()
        self._exigir_gestao(colecao)
        documento = documentos_visiveis(request.user).filter(id=documento_id).first()
        if documento is None:
            raise Http404
        colecao.documentos.remove(documento)
        colecao.save(update_fields=["atualizado_em"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    pagination_class = None
