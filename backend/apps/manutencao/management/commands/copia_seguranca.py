"""Cópia de segurança e restauração do Nexo (banco + arquivos). Ver docs/architecture/copia-de-seguranca.md.

    python manage.py copia_seguranca criar [--destino PASTA] [--sem-cifra]
    python manage.py copia_seguranca listar
    python manage.py copia_seguranca verificar ARQUIVO
    python manage.py copia_seguranca restaurar ARQUIVO --confirmar [--sem-copia-previa] [--forcar]

A senha vem de NEXO_BACKUP_SENHA (ou --senha / variável NEXO_BACKUP_SENHA_RESTAURACAO para cópias
feitas com outra senha).
"""

import os

from django.core.management.base import BaseCommand, CommandError

from apps.manutencao import copia


def _tamanho(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return f"{n:.0f} {unidade}" if unidade == "B" else f"{n:.1f} {unidade}".replace(".", ",")
        n /= 1024
    return str(n)


class Command(BaseCommand):
    help = "Cria, lista, verifica e restaura cópias de segurança do Nexo (banco + arquivos)."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="acao", required=True)
        c = sub.add_parser("criar", help="Gera uma cópia agora.")
        c.add_argument("--destino", help="Pasta de destino (padrão: NEXO_BACKUP_DIR).")
        c.add_argument("--sem-cifra", action="store_true", help="Permite gerar sem senha (não recomendado).")
        sub.add_parser("listar", help="Lista as cópias da pasta NEXO_BACKUP_DIR.")
        v = sub.add_parser("verificar", help="Confere integridade e legibilidade, sem alterar nada.")
        v.add_argument("arquivo")
        v.add_argument("--senha")
        r = sub.add_parser("restaurar", help="Substitui banco e arquivos pelo conteúdo da cópia.")
        r.add_argument("arquivo")
        r.add_argument("--senha")
        r.add_argument("--confirmar", action="store_true", help="Obrigatório: confirma a substituição.")
        r.add_argument("--sem-copia-previa", action="store_true", help="Não copia o estado atual antes.")
        r.add_argument("--forcar", action="store_true", help="Restaura mesmo com outras conexões no banco.")

    def handle(self, *args, acao, **op):
        try:
            getattr(self, f"_{acao}")(**op)
        except copia.ErroCopia as erro:
            raise CommandError(str(erro)) from erro

    def _senha(self, op):
        return op.get("senha") or os.environ.get("NEXO_BACKUP_SENHA_RESTAURACAO") or None

    def _criar(self, destino=None, sem_cifra=False, **_):
        r = copia.criar(destino=destino, sem_cifra=sem_cifra)
        cifra = "cifrada" if r.manifesto["cifrada"] else "SEM CIFRA"
        self.stdout.write(self.style.SUCCESS(f"Cópia criada: {r.caminho} ({_tamanho(r.bytes)}, {cifra})"))
        c = r.manifesto["contagens"]
        self.stdout.write(
            f"  {c['documentos']} documentos, {r.manifesto['arquivos']['quantidade']} arquivos, "
            f"{c['usuarios']} usuários, {c['eventos_auditoria']} eventos de auditoria"
        )

    def _listar(self, **_):
        copias = copia.listar()
        if not copias:
            self.stdout.write(f"Nenhuma cópia em {copia.pasta_copias()}")
            return
        for c in copias:
            cifra = "cifrada" if c.get("cifrada") else "sem cifra"
            self.stdout.write(f"{c['arquivo']}  {_tamanho(c['bytes'])}  {cifra}  {c.get('criada_em', '')[:19]}")

    def _verificar(self, arquivo, **op):
        r = copia.verificar(arquivo, self._senha(op))
        self.stdout.write(self.style.SUCCESS(f"Cópia íntegra: {r['arquivo']} (criada em {r['criada_em'][:19]})"))
        c = r["contagens"]
        self.stdout.write(
            f"  {c['documentos']} documentos, {r['arquivos']} arquivos, {c['usuarios']} usuários, "
            f"{r['objetos_no_banco']} objetos no banco; versão: {r['compatibilidade']}"
        )

    def _restaurar(self, arquivo, confirmar=False, sem_copia_previa=False, forcar=False, **op):
        if not confirmar:
            raise CommandError(
                "A restauração SUBSTITUI todo o banco e os arquivos do Nexo. Pare o Nexo e repita com --confirmar."
            )
        r = copia.restaurar(
            arquivo,
            self._senha(op),
            copia_previa=not sem_copia_previa,
            forcar=forcar,
            avisar=lambda t: self.stdout.write(t),
        )
        self.stdout.write(self.style.SUCCESS(f"Restaurado a partir da cópia de {r.manifesto['criada_em'][:19]}."))
        if r.copia_previa:
            self.stdout.write(f"  Estado anterior guardado em: {r.copia_previa}")
        if r.arquivos_antigos:
            self.stdout.write(f"  Arquivos anteriores mantidos em: {r.arquivos_antigos}")
        if not r.integridade_auditoria["integra"]:
            self.stdout.write(self.style.WARNING("  Atenção: a trilha de auditoria da cópia não está íntegra."))
        self.stdout.write("Inicie o Nexo novamente.")
