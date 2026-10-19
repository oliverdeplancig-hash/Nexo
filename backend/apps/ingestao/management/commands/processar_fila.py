import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.documentos.vigencia import avisar_revisoes
from apps.ingestao.pipeline import processar, proximo_da_fila
from apps.manutencao import saude

AVISOS_A_CADA_SEGUNDOS = 3600


class Command(BaseCommand):
    help = "Processa documentos recebidos (extração, metadados e indexação)."

    def add_arguments(self, parser):
        parser.add_argument("--continuo", action="store_true", help="Fica aguardando novos documentos.")
        parser.add_argument("--intervalo", type=float, default=3.0, help="Segundos entre verificações.")

    def handle(self, *args, continuo=False, intervalo=3.0, **opcoes):
        self.stdout.write("Worker de ingestão iniciado.")
        ultimo_aviso = 0.0
        while True:
            close_old_connections()
            if continuo and time.monotonic() - ultimo_aviso >= AVISOS_A_CADA_SEGUNDOS:
                # Avisos de revisão de documentos (idempotentes; ADR-015)
                try:
                    enviados = avisar_revisoes()
                    if enviados:
                        self.stdout.write(f"Avisos de revisão enviados: {enviados}")
                except Exception as erro:  # o worker de ingestão não pode parar por causa dos avisos
                    self.stderr.write(f"Falha ao avisar revisões: {erro}")
                try:  # problemas de saúde do sistema para os administradores (ADR-023)
                    avisados = saude.avisar()
                    if avisados:
                        self.stdout.write(f"Avisos de saúde do sistema enviados: {avisados}")
                except Exception as erro:
                    self.stderr.write(f"Falha ao verificar a saúde do sistema: {erro}")
                ultimo_aviso = time.monotonic()
            if continuo:
                try:
                    saude.sinal_de_vida(saude.PROCESSO_FILA)  # o painel de saúde sabe que o processador está vivo
                except Exception as erro:
                    self.stderr.write(f"Falha ao registrar sinal de vida: {erro}")
            documento = proximo_da_fila()
            if documento:
                self.stdout.write(f"Processando documento {documento.id}: {documento.titulo}")
                processar(documento)
                self.stdout.write(f"  -> {documento.status}")
                continue
            if not continuo:
                break
            time.sleep(intervalo)
