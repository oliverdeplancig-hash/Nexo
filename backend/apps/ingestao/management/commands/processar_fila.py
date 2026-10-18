import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.ingestao.pipeline import processar, proximo_da_fila


class Command(BaseCommand):
    help = "Processa documentos recebidos (extração, metadados e indexação)."

    def add_arguments(self, parser):
        parser.add_argument("--continuo", action="store_true", help="Fica aguardando novos documentos.")
        parser.add_argument("--intervalo", type=float, default=3.0, help="Segundos entre verificações.")

    def handle(self, *args, continuo=False, intervalo=3.0, **opcoes):
        self.stdout.write("Worker de ingestão iniciado.")
        while True:
            close_old_connections()
            documento = proximo_da_fila()
            if documento:
                self.stdout.write(f"Processando documento {documento.id}: {documento.titulo}")
                processar(documento)
                self.stdout.write(f"  -> {documento.status}")
                continue
            if not continuo:
                break
            time.sleep(intervalo)
