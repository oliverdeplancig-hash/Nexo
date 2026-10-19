"""Saúde do sistema (ADR-023): o que o administrador precisa saber para manter o Nexo funcionando.

Cada verificação devolve uma situação — "ok", "atencao" ou "problema" — com um texto curto e, quando houver,
o que fazer. Nada aqui mostra conteúdo de documentos, nomes de pessoas ou senhas: só números e estados.

Verificações: banco, espaço em disco, cópias de segurança, processamento de documentos, IA local, certificado
HTTPS e configuração de produção. `avisar()` notifica os administradores dos problemas, uma vez por dia por
assunto; o processador da fila chama a cada hora.
"""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

from nexo.versao import VERSAO

from .models import SinalDeVida

OK, ATENCAO, PROBLEMA = "ok", "atencao", "problema"
_ORDEM = {OK: 0, ATENCAO: 1, PROBLEMA: 2}

PROCESSO_FILA = "processador_fila"
SINAL_A_CADA = timedelta(seconds=30)
SINAL_ATRASADO = timedelta(minutes=3)
DISCO_ATENCAO = 0.15  # fração livre
DISCO_PROBLEMA = 0.05
CERTIFICADO_ATENCAO_DIAS = 30


@dataclass
class Verificacao:
    codigo: str
    titulo: str
    situacao: str
    resumo: str
    acao: str = ""
    detalhes: dict | None = None


# --------------------------------------------------------------------------
# Sinal de vida dos processos de apoio
# --------------------------------------------------------------------------
_ultimo_sinal: dict[str, datetime] = {}


def sinal_de_vida(processo: str, **detalhes) -> None:
    """Chamado em laço pelo processo; grava no máximo a cada 30 s."""
    agora = timezone.now()
    if processo in _ultimo_sinal and agora - _ultimo_sinal[processo] < SINAL_A_CADA:
        return
    SinalDeVida.objects.update_or_create(processo=processo, defaults={"atualizado_em": agora, "detalhes": detalhes})
    _ultimo_sinal[processo] = agora


# --------------------------------------------------------------------------
# Verificações
# --------------------------------------------------------------------------
def _tamanho(n: float) -> str:
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unidade == "TB":
            return f"{n:.1f} {unidade}".replace(".0 ", " ").replace(".", ",")
        n /= 1024
    return ""


def verificar_banco() -> Verificacao:
    try:
        with connection.cursor() as c:
            c.execute("SELECT current_setting('server_version'), pg_database_size(current_database())")
            versao, tamanho = c.fetchone()
            c.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'unaccent')")
            extensoes = sorted(r[0] for r in c.fetchall())
    except Exception as erro:  # pragma: no cover - depende de infraestrutura
        return Verificacao(
            "banco", "Banco de dados", PROBLEMA, "O banco não respondeu.", detalhes={"erro": type(erro).__name__}
        )
    faltam = {"vector", "unaccent"} - set(extensoes)
    return Verificacao(
        "banco",
        "Banco de dados",
        PROBLEMA if faltam else OK,
        f"PostgreSQL {versao.split()[0]}, {_tamanho(tamanho)}."
        + (f" Faltam as extensões: {', '.join(sorted(faltam))}." if faltam else ""),
        "Instale as extensões indicadas (docs/database/README.md)." if faltam else "",
        {"versao": versao.split()[0], "bytes": tamanho, "extensoes": extensoes},
    )


def _uso(pasta: Path) -> tuple[int, int] | None:
    alvo = Path(pasta)
    while not alvo.exists() and alvo != alvo.parent:
        alvo = alvo.parent
    try:
        uso = shutil.disk_usage(alvo)
    except OSError:
        return None
    return uso.free, uso.total


def verificar_disco() -> Verificacao:
    pastas = {"documentos": settings.NEXO_ARMAZENAMENTO_DIR, "copias": settings.NEXO_BACKUP["DIR"]}
    pior, partes, detalhes = OK, [], {}
    for nome, pasta in pastas.items():
        uso = _uso(pasta)
        if not uso:
            continue
        livre, total = uso
        if any(d == {"livre": livre, "total": total} for d in detalhes.values()):
            partes[0] = partes[0].replace("Documentos:", "Documentos e cópias:")
            continue  # mesma unidade de disco: mostra uma vez só
        fracao = livre / total if total else 0
        situacao = PROBLEMA if fracao < DISCO_PROBLEMA else ATENCAO if fracao < DISCO_ATENCAO else OK
        pior = max(pior, situacao, key=_ORDEM.get)
        rotulo = "Documentos" if nome == "documentos" else "Cópias"
        partes.append(f"{rotulo}: {_tamanho(livre)} livres de {_tamanho(total)} ({fracao:.0%})")
        detalhes[nome] = {"livre": livre, "total": total}
    acao = "Libere espaço ou aumente o disco antes que as cópias e as importações falhem." if pior != OK else ""
    return Verificacao(
        "disco", "Espaço em disco", pior, "; ".join(partes) + "." if partes else "Sem dados.", acao, detalhes
    )


def verificar_copias() -> Verificacao:
    from . import copia

    cfg = settings.NEXO_BACKUP
    agendadas = [c for c in copia.listar() if c.get("rotulo", "nexo") == copia.ROTULO_AGENDADA and c.get("criada_em")]
    if not agendadas:
        return Verificacao(
            "copias",
            "Cópias de segurança",
            PROBLEMA,
            "Nenhuma cópia de segurança foi feita ainda.",
            "Agende a cópia diária (Windows: scripts\\agendar-copia-windows.cmd; Linux: nexo-copia.timer).",
        )
    horas = (timezone.now() - datetime.fromisoformat(agendadas[0]["criada_em"])).total_seconds() / 3600
    sem_cifra = not cfg["SENHA"]
    if horas > cfg["ALERTA_HORAS"]:
        situacao, resumo = PROBLEMA, f"A última cópia tem {horas:.0f} h (limite de {cfg['ALERTA_HORAS']} h)."
        acao = "Verifique o agendamento e o registro da cópia de segurança."
    else:
        situacao, resumo, acao = OK, f"Última cópia há {horas:.0f} h.", ""
    if sem_cifra:
        situacao = max(situacao, ATENCAO, key=_ORDEM.get)
        resumo += " As cópias estão sem cifra."
        acao = acao or "Defina NEXO_BACKUP_SENHA e guarde a senha fora do servidor."
    return Verificacao("copias", "Cópias de segurança", situacao, resumo, acao, {"horas": round(horas, 1)})


def verificar_processamento() -> Verificacao:
    from apps.documentos.models import Documento, StatusDocumento
    from apps.ingestao.models import EtapaProcessamento

    em_fila = Documento.objects.filter(
        status__in=[
            StatusDocumento.RECEBIDO,
            StatusDocumento.EXTRAINDO,
            StatusDocumento.METADADOS,
            StatusDocumento.INDEXANDO,
        ]
    ).count()
    falhas = Documento.objects.filter(status=StatusDocumento.FALHA).count()
    erros_7d = EtapaProcessamento.objects.filter(
        situacao=EtapaProcessamento.Situacao.ERRO, ocorrido_em__gte=timezone.now() - timedelta(days=7)
    ).count()
    detalhes = {"em_fila": em_fila, "com_falha": falhas, "erros_7_dias": erros_7d}
    imediato = settings.NEXO_INGESTAO.get("PROCESSAR_IMEDIATAMENTE", False)
    sinal = SinalDeVida.objects.filter(processo=PROCESSO_FILA).first()
    partes = [f"{em_fila} na fila", f"{falhas} com falha"]
    if imediato:
        situacao, acao = OK, ""
        partes.append("processamento na hora da importação")
    elif not sinal or timezone.now() - sinal.atualizado_em > SINAL_ATRASADO:
        situacao = PROBLEMA if em_fila else ATENCAO
        partes.append(
            "processador da fila sem sinal"
            + (f" desde {timezone.localtime(sinal.atualizado_em):%d/%m %H:%M}" if sinal else "")
        )
        acao = "Verifique se o processador da fila está rodando (processar_fila --continuo)."
    else:
        situacao, acao = OK, ""
        partes.append("processador da fila ativo")
    if falhas and situacao == OK:
        situacao = ATENCAO
        acao = "Abra os documentos com falha em Importar documentos para ver o motivo."
    return Verificacao(
        "processamento", "Processamento de documentos", situacao, ", ".join(partes) + ".", acao, detalhes
    )


def verificar_ia() -> Verificacao:
    import httpx

    from apps.ia.fila import situacao as situacao_fila
    from apps.ia.provedores import obter_provedor

    cfg = settings.NEXO_IA
    fila = situacao_fila()
    detalhes = {"provedor": cfg["PROVEDOR"], "fila": fila}
    if cfg["PROVEDOR"] == "falso":
        return Verificacao(
            "ia",
            "IA local",
            ATENCAO,
            "Provedor de teste: o assistente responde só por regras e trechos.",
            "Instale o Ollama e defina NEXO_IA_PROVEDOR=ollama para respostas escritas pela IA.",
            detalhes,
        )
    if not obter_provedor().disponivel():
        return Verificacao(
            "ia",
            "IA local",
            PROBLEMA,
            "O Ollama não respondeu. Perguntas sem regra recebem só os trechos dos documentos.",
            "Inicie o Ollama no servidor de IA (NEXO_OLLAMA_URL).",
            detalhes,
        )
    try:
        nomes = {
            m.get("name", "") for m in httpx.get(f"{cfg['OLLAMA_URL']}/api/tags", timeout=3).json().get("models", [])
        }
    except (httpx.HTTPError, ValueError):
        nomes = set()

    def instalado(modelo: str) -> bool:
        return modelo in nomes or f"{modelo}:latest" in nomes

    faltam = [m for m in (cfg["MODELO_CHAT"], cfg["MODELO_EMBEDDING"]) if nomes and not instalado(m)]
    resumo = (
        f"Ollama ativo, modelo {cfg['MODELO_CHAT']}. Agora: {fila['gerando']} gerando, {fila['esperando']} na fila."
    )
    if faltam:
        return Verificacao(
            "ia",
            "IA local",
            PROBLEMA,
            f"Modelos não baixados: {', '.join(faltam)}.",
            "Rode scripts\\ativar-ia-local.cmd.",
            detalhes,
        )
    return Verificacao("ia", "IA local", OK, resumo, "", detalhes)


def verificar_certificado(pasta: Path | None = None) -> Verificacao | None:
    """Só no servidor Windows (o certificado do nginx é cuidado pela TI no Linux)."""
    arquivo = Path(pasta or Path(settings.BASE_DIR) / ".certificados") / "nexo.crt"
    if not arquivo.exists():
        return None
    from cryptography import x509

    try:
        cert = x509.load_pem_x509_certificate(arquivo.read_bytes())
    except ValueError:
        return Verificacao(
            "certificado", "Certificado HTTPS", PROBLEMA, "O arquivo nexo.crt não é um certificado válido."
        )
    vence = cert.not_valid_after_utc
    dias = (vence - timezone.now()).days
    autoassinado = cert.issuer == cert.subject
    resumo = f"Vence em {timezone.localtime(vence):%d/%m/%Y} ({dias} dias)."
    if autoassinado:
        resumo += " Autoassinado: distribua nexo.cer aos computadores ou use o certificado da TI."
    if dias < 0:
        situacao, acao = PROBLEMA, "Gere um novo: manage.py gerar_certificado --substituir, e reinicie o servidor."
    elif dias < CERTIFICADO_ATENCAO_DIAS:
        situacao, acao = ATENCAO, "Renove o certificado antes do vencimento."
    else:
        situacao, acao = OK, ""
    return Verificacao(
        "certificado", "Certificado HTTPS", situacao, resumo, acao, {"dias": dias, "autoassinado": autoassinado}
    )


def verificar_configuracao() -> Verificacao:
    from apps.contas.credenciais import email_configurado

    problemas, avisos = [], []
    if settings.DEBUG:
        problemas.append("modo de depuração ligado (NEXO_DEBUG)")
    if not settings.SESSION_COOKIE_SECURE and not settings.DEBUG:
        avisos.append("cookies sem a marca de seguro (NEXO_COOKIE_SEGURO)")
    if not email_configurado():
        avisos.append("e-mail não configurado: senhas de novos usuários aparecem só na tela")
    entra = getattr(settings, "NEXO_ENTRA", {}) or {}
    login = "conta Microsoft" if entra.get("CLIENT_ID") else "senha local"
    resumo = f"Versão {VERSAO}, entrada por {login}."
    if problemas or avisos:
        texto = "; ".join(problemas + avisos)
        resumo += " " + texto[0].upper() + texto[1:] + "."
    return Verificacao(
        "configuracao",
        "Configuração",
        PROBLEMA if problemas else ATENCAO if avisos else OK,
        resumo,
        "Rode manage.py preparar_producao e revise o backend/.env." if problemas else "",
        {"versao": VERSAO, "debug": settings.DEBUG, "email": email_configurado(), "login": login},
    )


def verificar() -> dict:
    itens = [
        verificar_configuracao(),
        verificar_banco(),
        verificar_disco(),
        verificar_copias(),
        verificar_processamento(),
        verificar_ia(),
        verificar_certificado(),
    ]
    itens = [i for i in itens if i is not None]
    geral = max((i.situacao for i in itens), key=_ORDEM.get, default=OK)
    return {"situacao": geral, "versao": VERSAO, "verificado_em": timezone.now(), "itens": [asdict(i) for i in itens]}


# --------------------------------------------------------------------------
# Avisos aos administradores
# --------------------------------------------------------------------------
AVISAR = {"disco", "copias", "processamento", "certificado", "banco", "ia"}


def avisar() -> int:
    """Notifica quem administra permissões sobre problemas, no máximo uma vez por dia por assunto."""
    from apps.contas.models import Funcao, Usuario
    from apps.notificacoes.models import Notificacao
    from apps.notificacoes.servico import notificar

    resultado = verificar()
    pendentes = [i for i in resultado["itens"] if i["codigo"] in AVISAR and i["situacao"] == PROBLEMA]
    if not pendentes:
        return 0
    hoje = timezone.localdate().isoformat()
    destinatarios = [u for u in Usuario.objects.filter(is_active=True) if u.tem_funcao(Funcao.ADMIN_PERMISSOES)]
    enviados = 0
    for item in pendentes:
        for usuario in destinatarios:
            ja = Notificacao.objects.filter(
                usuario=usuario, tipo="saude_sistema", dados__codigo=item["codigo"], dados__dia=hoje
            ).exists()
            if ja:
                continue
            notificar(
                usuario,
                "saude_sistema",
                f"{item['titulo']}: precisa de atenção",
                f"{item['resumo']} {item['acao']}".strip(),
                link="/administracao?aba=saude",
                dados={"codigo": item["codigo"], "dia": hoje},
            )
            enviados += 1
    return enviados
