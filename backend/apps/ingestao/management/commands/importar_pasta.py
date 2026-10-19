"""Importa todos os arquivos de uma pasta para o acervo, com os mesmos metadados (carga inicial do acervo real).

Usa o mesmo caminho da tela de importação (validação de formato e assinatura, auditoria, fila de
processamento e permissões). Arquivos já importados (mesmo conteúdo) são pulados.

    python manage.py importar_pasta "D:\\Acervo\\CCP" --usuario nome.sobrenome --setor CCP --classificacao geral
"""

import hashlib
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings

from apps.acesso.models import Classificacao
from apps.contas.models import Funcao, Usuario
from apps.documentos.models import Documento, StatusDocumento
from apps.ingestao.pipeline import extensao_valida, processar, proximo_da_fila
from apps.ingestao.views import _criar_documento
from apps.organizacao.models import Setor


class Command(BaseCommand):
    help = "Importa os arquivos de uma pasta (PDF, DOCX, TXT, MD, HTML e imagens com OCR) para o acervo."

    def add_arguments(self, parser):
        parser.add_argument("pasta")
        parser.add_argument("--usuario", required=True, help="Quem importa (precisa da função de importar).")
        parser.add_argument("--setor", required=True, help="Sigla do setor responsável.")
        parser.add_argument("--classificacao", default=Classificacao.SETOR, choices=Classificacao.values)
        parser.add_argument("--recursivo", action="store_true", help="Inclui as subpastas.")
        parser.add_argument("--simular", action="store_true", help="Só lista o que seria importado.")
        parser.add_argument(
            "--sem-processar",
            action="store_true",
            help="Só coloca na fila; o processador da fila (processar_fila) faz a extração e a indexação.",
        )

    def handle(self, *args, pasta, usuario, setor, classificacao, recursivo, simular, sem_processar=False, **opcoes):
        # A importação em lote nunca dispara o processamento em segundo plano da instalação local:
        # ou processa aqui, em sequência, ou deixa para o processador da fila.
        with override_settings(NEXO_INGESTAO={**settings.NEXO_INGESTAO, "PROCESSAR_IMEDIATAMENTE": False}):
            self._importar(pasta, usuario, setor, classificacao, recursivo, simular, sem_processar)

    def _importar(self, pasta, usuario, setor, classificacao, recursivo, simular, sem_processar):
        raiz = Path(pasta)
        if not raiz.is_dir():
            raise CommandError(f"Pasta não encontrada: {raiz}")
        pessoa = Usuario.objects.filter(username=usuario, is_active=True).first()
        if not pessoa or not pessoa.tem_funcao(Funcao.IMPORTAR_DOCUMENTOS):
            raise CommandError("Usuário inexistente, inativo ou sem a função de importar documentos.")
        unidade = Setor.objects.filter(sigla__iexact=setor, ativo=True).first()
        if not unidade:
            raise CommandError(f"Setor não encontrado: {setor}. Cadastre-o em Setores e contatos.")

        arquivos = sorted(p for p in (raiz.rglob("*") if recursivo else raiz.iterdir()) if p.is_file())
        validos = [p for p in arquivos if extensao_valida(p.name)]
        self.stdout.write(f"{len(validos)} de {len(arquivos)} arquivos em formato aceito.")
        if simular:
            for p in validos:
                self.stdout.write(f"  {p.relative_to(raiz)}")
            return

        requisicao = SimpleNamespace(user=pessoa, META={}, data={})
        metadados = {
            "titulo": "",
            "descricao": "",
            "categoria": None,
            "palavras_chave": [],
            "data_documento": None,
            "numero_referencia": "",
            "setor": unidade,
            "responsavel": pessoa.id,
            "classificacao": classificacao,
            "permite_download_geral": False,
            "autorizados_baixam": False,
            "setores_autorizados": [],
            "perfis_autorizados": [],
            "colecoes": [],
            "revisar_em": None,
        }
        importados = pulados = falhas = 0
        for caminho in validos:
            hash_hex = hashlib.sha256(caminho.read_bytes()).hexdigest()
            if Documento.objects.filter(hash_sha256=hash_hex).exclude(status=StatusDocumento.ARQUIVADO).exists():
                pulados += 1
                self.stdout.write(f"  já existe: {caminho.name}")
                continue
            with caminho.open("rb") as aberto:
                arquivo = File(aberto, name=caminho.name)
                resultado = _criar_documento(requisicao, arquivo, dict(metadados))
            if "erro" in resultado:
                falhas += 1
                self.stderr.write(f"  ERRO {caminho.name}: {resultado['erro']}")
            else:
                importados += 1
                self.stdout.write(f"  importado: {caminho.name} (documento {resultado['id']}, {resultado['status']})")
        self.stdout.write(
            self.style.SUCCESS(f"Importados: {importados} · já existentes: {pulados} · com erro: {falhas}")
        )
        if sem_processar or not importados:
            return
        self.stdout.write("Processando (extração, metadados e indexação)…")
        while documento := proximo_da_fila():
            processar(documento)
            self.stdout.write(f"  {documento.titulo}: {documento.get_status_display()}")
