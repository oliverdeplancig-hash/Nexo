"""Carrega dados de DEMONSTRAÇÃO (fictícios e identificados como exemplo).

Nunca use em produção: cria usuários com senha conhecida.
"""

from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.acesso.models import Classificacao
from apps.contas.models import Perfil, Usuario
from apps.documentos.models import Categoria, Documento
from apps.ingestao.pipeline import processar
from apps.motor.models import FonteRegra, Regra, StatusRegra, TipoRegra
from apps.organizacao.models import Setor

SENHA_DEMO = "Nexo@demo2026"
PASTA = Path(settings.BASE_DIR) / "demo" / "documentos"

SETORES = [
    {
        "sigla": "GP",
        "nome": "Gestão de Pessoas (exemplo)",
        "descricao": "Atende demandas funcionais dos servidores.",
        "competencias": "Férias, licenças, frequência, cadastro funcional e benefícios.",
        "tipos_demanda": ["férias", "licenças", "frequência", "benefícios"],
        "servicos": ["Homologação de férias", "Atualização cadastral"],
        "palavras_chave": ["férias", "licença", "ponto", "frequência", "servidor", "benefício"],
        "orientacao_acesso": "Envie a solicitação pelo canal institucional do setor, informando sua matrícula.",
    },
    {
        "sigla": "TI",
        "nome": "Tecnologia da Informação (exemplo)",
        "descricao": "Suporte técnico, sistemas, rede e segurança da informação.",
        "competencias": "Senhas de rede, contas de usuário, estações de trabalho, sistemas e segurança da informação.",
        "tipos_demanda": ["senha", "acesso a sistemas", "suporte técnico"],
        "servicos": ["Redefinição de senha", "Criação de contas", "Suporte a estações"],
        "palavras_chave": ["senha", "rede", "computador", "sistema", "acesso", "suporte", "email"],
        "orientacao_acesso": "Abra um chamado no canal de suporte técnico da instituição.",
    },
    {
        "sigla": "PROT",
        "nome": "Protocolo e Arquivo (exemplo)",
        "descricao": "Recebimento, registro e tramitação de documentos e processos.",
        "competencias": "Abertura de processos, tramitação, arquivo e solicitações de acesso a documentos.",
        "tipos_demanda": ["processo", "protocolo", "arquivo", "acesso a documento"],
        "servicos": ["Abertura de processo", "Consulta de tramitação"],
        "palavras_chave": ["processo", "protocolo", "requerimento", "arquivo", "tramitação", "documento"],
        "orientacao_acesso": "Solicite formalmente ao setor responsável pelo documento, com justificativa.",
    },
]

DOCUMENTOS = [
    ("ferias.md", "Procedimento de solicitação de férias (exemplo)", "GP", Classificacao.GERAL, "Procedimento"),
    ("protocolo.md", "Manual do protocolo de documentos (exemplo)", "PROT", Classificacao.GERAL, "Manual"),
    (
        "seguranca-informacao.md",
        "Norma interna de segurança da informação (exemplo)",
        "TI",
        Classificacao.SETOR,
        "Norma",
    ),
    ("contingencia.md", "Plano de contingência de sistemas (exemplo)", "TI", Classificacao.RESTRITO, "Orientação"),
]


class Command(BaseCommand):
    help = "Carrega setores, usuários, documentos e regras de demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true", help="Permite rodar com DEBUG desligado.")

    @transaction.atomic
    def handle(self, *args, forcar=False, **opcoes):
        if not settings.DEBUG and not forcar:
            raise CommandError("Dados de demonstração só com NEXO_DEBUG=true (ou --forcar).")
        call_command("inicializar_nexo")

        setores = {}
        for dados in SETORES:
            setor, _ = Setor.objects.update_or_create(sigla=dados["sigla"], defaults=dados)
            setores[setor.sigla] = setor

        perfis = {p.codigo: p for p in Perfil.objects.all()}
        usuarios = {
            "admin.demo": ("Administração (demo)", "TI", list(perfis.values())),
            "servidor.demo": ("Servidor (demo)", "GP", [perfis["servidor"]]),
            "ti.demo": ("Analista de TI (demo)", "TI", [perfis["servidor"], perfis["gestor-documental"]]),
        }
        criados = {}
        for login, (nome, sigla, lista_perfis) in usuarios.items():
            usuario, criado = Usuario.objects.get_or_create(
                username=login, defaults={"nome_exibicao": nome, "setor": setores[sigla]}
            )
            if criado:
                usuario.set_password(SENHA_DEMO)
                usuario.save()
            usuario.perfis.set(lista_perfis)
            criados[login] = usuario

        documentos = {}
        for arquivo, titulo, sigla, classificacao, categoria in DOCUMENTOS:
            doc = Documento.objects.filter(titulo=titulo).first()
            if doc is None:
                conteudo = (PASTA / arquivo).read_bytes()
                doc = Documento(
                    titulo=titulo,
                    descricao="Documento fictício de demonstração.",
                    categoria=Categoria.objects.get(nome=categoria),
                    setor_responsavel=setores[sigla],
                    responsavel=criados["ti.demo"] if sigla == "TI" else criados["admin.demo"],
                    criado_por=criados["admin.demo"],
                    classificacao=classificacao,
                    permite_download_geral=classificacao == Classificacao.GERAL,
                    nome_arquivo_original=arquivo,
                    tipo_arquivo="md",
                    tamanho_bytes=len(conteudo),
                    hash_sha256=__import__("hashlib").sha256(conteudo).hexdigest(),
                )
                doc.arquivo.save(arquivo, ContentFile(conteudo), save=False)
                doc.save()
                processar(doc)
            documentos[arquivo] = doc

        regras = [
            {
                "codigo": "MD-001",
                "titulo": "Como solicitar férias",
                "tipo": TipoRegra.PROCEDIMENTO,
                "frases_exemplo": [
                    "Como solicito férias?",
                    "Qual o procedimento para pedir férias?",
                    "Quero marcar minhas férias",
                    "prazo para solicitar férias",
                ],
                "palavras_chave": ["férias", "solicitar", "marcar", "prazo"],
                "termos_obrigatorios": ["férias"],
                "resposta": "Para solicitar férias, registre o pedido com **antecedência mínima de 30 dias** "
                "da data de início, seguindo as etapas abaixo.",
                "etapas": [
                    {
                        "titulo": "Consulte o saldo",
                        "descricao": "Verifique o saldo de férias no sistema de gestão de pessoas.",
                    },
                    {"titulo": "Preencha o formulário", "descricao": "Indique o período pretendido."},
                    {"titulo": "Obtenha a ciência da chefia", "descricao": "A chefia imediata deve registrar ciência."},
                    {"titulo": "Encaminhe à Gestão de Pessoas", "descricao": "Acompanhe a homologação pelo sistema."},
                ],
                "setor": "GP",
                "fonte": ("ferias.md", "3. Etapas", "1. Consultar o saldo de férias no sistema de gestão de pessoas."),
            },
            {
                "codigo": "MD-002",
                "titulo": "Como solicitar acesso a documento restrito",
                "tipo": TipoRegra.ORIENTACAO_ACESSO,
                "frases_exemplo": [
                    "Como peço acesso a um documento restrito?",
                    "Não consigo abrir um documento, como solicitar acesso?",
                    "solicitar acesso a documento",
                ],
                "palavras_chave": ["acesso", "documento", "restrito", "solicitar", "permissão"],
                "termos_obrigatorios": ["acesso"],
                "resposta": "O acesso a documento restrito é solicitado **formalmente ao setor responsável pelo documento**, "
                "com a justificativa da necessidade de conhecimento. Se aprovado, a autorização é registrada no "
                "repositório com prazo de validade.",
                "etapas": [],
                "setor": "PROT",
                "fonte": (
                    "protocolo.md",
                    "Solicitação de acesso a documentos restritos",
                    "O acesso a documento restrito deve ser solicitado formalmente ao setor responsável pelo documento",
                ),
            },
            {
                "codigo": "MD-003",
                "titulo": "Redefinição de senha de rede",
                "tipo": TipoRegra.ROTEAMENTO,
                "frases_exemplo": [
                    "Esqueci minha senha de rede",
                    "Como redefinir a senha da rede?",
                    "minha senha expirou",
                ],
                "palavras_chave": ["senha", "rede", "redefinir", "expirou", "bloqueada"],
                "termos_obrigatorios": ["senha"],
                "resposta": "A redefinição de senha de rede é feita pela **{setor_responsavel}**, mediante confirmação "
                "de identidade. A nova senha deve ter no mínimo 12 caracteres.",
                "etapas": [],
                "setor": "TI",
                "fonte": (
                    "seguranca-informacao.md",
                    "Senhas de rede",
                    "A redefinição de senha é feita pelo setor de Tecnologia da Informação mediante confirmação de identidade.",
                ),
            },
        ]
        for dados in regras:
            arquivo, secao, trecho = dados.pop("fonte")
            setor = setores[dados.pop("setor")]
            regra, _ = Regra.objects.update_or_create(
                codigo=dados["codigo"],
                defaults={
                    **dados,
                    "setor_responsavel": setor,
                    "status": StatusRegra.PUBLICADA,
                    "publicada_em": timezone.now(),
                    "versao": 1,
                    "criada_por": criados["admin.demo"],
                },
            )
            regra.fontes.all().delete()
            FonteRegra.objects.create(regra=regra, documento=documentos[arquivo], secao=secao, trecho_citado=trecho)

        self.stdout.write(self.style.SUCCESS("Demonstração carregada."))
        self.stdout.write(f"Usuários: admin.demo, servidor.demo, ti.demo — senha: {SENHA_DEMO}")
