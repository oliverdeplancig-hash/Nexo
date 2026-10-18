from django.core.management.base import BaseCommand

from apps.documentos.models import Documento, StatusDocumento
from apps.ingestao.pipeline import _indexar_semantica


class Command(BaseCommand):
    help = "Gera embeddings de documentos disponíveis que ficaram só com busca textual."

    def add_arguments(self, parser):
        parser.add_argument("--todos", action="store_true", help="Refaz também os já indexados (troca de modelo).")

    def handle(self, *args, todos=False, **opcoes):
        qs = Documento.objects.filter(status=StatusDocumento.DISPONIVEL)
        if not todos:
            qs = qs.filter(indexacao_semantica=False)
        for documento in qs.order_by("id"):
            aviso = _indexar_semantica(documento)
            self.stdout.write(f"{documento.id}: {'aviso — ' + aviso if aviso else 'ok'}")
            if aviso:
                break
