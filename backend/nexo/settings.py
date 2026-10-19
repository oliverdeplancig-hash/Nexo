"""Configurações do Nexo.

Todas as variáveis sensíveis ou dependentes de ambiente vêm do arquivo `.env`
(ver `.env.example` na raiz do backend). Nenhum segredo deve ser versionado.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

# --------------------------------------------------------------------------
# Núcleo
# --------------------------------------------------------------------------
SECRET_KEY = env("NEXO_SECRET_KEY", default="dev-inseguro-troque-em-producao")
DEBUG = env.bool("NEXO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("NEXO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list(
    "NEXO_CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "channels",
    # Apps do Nexo
    "apps.comum",
    "apps.organizacao",
    "apps.contas",
    "apps.acesso",
    "apps.documentos",
    "apps.ingestao",
    "apps.busca",
    "apps.motor",
    "apps.ia",
    "apps.conversas",
    "apps.auditoria",
    "apps.notificacoes",
    "apps.manutencao",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.contas.credenciais.ExigeTrocaDeSenha",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nexo.urls"
WSGI_APPLICATION = "nexo.wsgi.application"
ASGI_APPLICATION = "nexo.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# --------------------------------------------------------------------------
# Banco de dados — PostgreSQL (>= 15) com as extensões vector e unaccent
# --------------------------------------------------------------------------
DATABASES = {"default": env.db("NEXO_DATABASE_URL", default="postgres://nexo:nexo@localhost:5432/nexo")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("NEXO_DB_CONN_MAX_AGE", default=60)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "contas.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Localização
# --------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = env("NEXO_TIME_ZONE", default="America/Bahia")
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Arquivos
# --------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Os documentos NUNCA são servidos diretamente pelo servidor web: o download
# passa por uma view que aplica o motor de permissões e registra auditoria.
NEXO_ARMAZENAMENTO_DIR = Path(env("NEXO_ARMAZENAMENTO_DIR", default=str(BASE_DIR / "armazenamento")))
NEXO_UPLOAD_MAX_MB = env.int("NEXO_UPLOAD_MAX_MB", default=50)
NEXO_FORMATOS_ACEITOS = [".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".png", ".jpg", ".jpeg", ".tif", ".tiff"]
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --------------------------------------------------------------------------
# Segurança de sessão
# --------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = env.int("NEXO_SESSAO_SEGUNDOS", default=8 * 60 * 60)
SESSION_COOKIE_SECURE = env.bool("NEXO_COOKIE_SEGURO", default=not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_HTTPONLY = False  # o SPA lê o token para enviar no cabeçalho X-CSRFToken
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"  # o visualizador de PDF usa iframe da mesma origem

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.comum.paginacao.PaginacaoPadrao",
    "PAGE_SIZE": 20,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "user": env("NEXO_LIMITE_REQUISICOES", default="600/min"),
        # Tentativas de login por IP. Só os testes de ponta a ponta afrouxam este limite.
        "login": env("NEXO_LIMITE_LOGIN", default="10/min"),
    },
}

# --------------------------------------------------------------------------
# Channels (WebSocket)
# Local/usuário único: InMemory. Servidor com vários processos: Redis.
# --------------------------------------------------------------------------
_REDIS_URL = env("NEXO_REDIS_URL", default="")
if _REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# --------------------------------------------------------------------------
# Inteligência artificial (ver docs/architecture/ia-e-motor.md)
# --------------------------------------------------------------------------
NEXO_IA = {
    # "ollama" em produção; "falso" em testes e demonstrações sem LLM.
    "PROVEDOR": env("NEXO_IA_PROVEDOR", default="ollama"),
    "OLLAMA_URL": env("NEXO_OLLAMA_URL", default="http://localhost:11434"),
    "MODELO_CHAT": env("NEXO_MODELO_CHAT", default="qwen2.5:7b-instruct"),
    "MODELO_EMBEDDING": env("NEXO_MODELO_EMBEDDING", default="bge-m3"),
    # Alterar a dimensão exige nova migração do campo Trecho.embedding.
    "DIMENSAO_EMBEDDING": env.int("NEXO_DIMENSAO_EMBEDDING", default=1024),
    "TEMPERATURA": env.float("NEXO_TEMPERATURA", default=0.1),
    "CONTEXTO_MAX_TRECHOS": env.int("NEXO_CONTEXTO_MAX_TRECHOS", default=6),
    "SIMILARIDADE_MINIMA": env.float("NEXO_SIMILARIDADE_MINIMA", default=0.45),
    "TIMEOUT_SEGUNDOS": env.float("NEXO_IA_TIMEOUT", default=120.0),
}

NEXO_MOTOR = {
    # Pontuação mínima para o motor determinístico responder sem LLM.
    "LIMIAR": env.float("NEXO_MOTOR_LIMIAR", default=0.62),
    # Se as duas melhores regras ficarem a menos desta distância, o motor
    # pede desambiguação em vez de escolher sozinho.
    "MARGEM_AMBIGUIDADE": env.float("NEXO_MOTOR_MARGEM", default=0.04),
}

# OCR para documentos digitalizados (ADR-009). "tesseract" ou "desligado".
NEXO_OCR = {
    "MOTOR": env("NEXO_OCR_MOTOR", default="tesseract"),
    "TESSERACT_CMD": env("NEXO_TESSERACT_CMD", default=""),
    "TESSDATA_DIR": env("NEXO_TESSDATA_DIR", default=""),
    "IDIOMA": env("NEXO_OCR_IDIOMA", default="por"),
    "DPI": env.int("NEXO_OCR_DPI", default=300),
}

# Login institucional pela conta Microsoft (Entra ID) — ADR-010. Ativo quando os três primeiros estão definidos.
NEXO_ENTRA = {
    "TENANT_ID": env("NEXO_ENTRA_TENANT_ID", default=""),
    "CLIENT_ID": env("NEXO_ENTRA_CLIENT_ID", default=""),
    "CLIENT_SECRET": env("NEXO_ENTRA_CLIENT_SECRET", default=""),
    "AUTORIDADE": env("NEXO_ENTRA_AUTORIDADE", default="https://login.microsoftonline.com"),
    # Vazio = derivado da requisição (http(s)://<host>/api/v1/auth/microsoft/retorno/)
    "REDIRECT_URI": env("NEXO_ENTRA_REDIRECT_URI", default=""),
    "DOMINIOS": env.list("NEXO_ENTRA_DOMINIOS", default=[]),
    "CRIAR_USUARIOS": env.bool("NEXO_ENTRA_CRIAR_USUARIOS", default=True),
    "PERFIL_PADRAO": env("NEXO_ENTRA_PERFIL_PADRAO", default="servidor"),
    "ROTULO": env("NEXO_ENTRA_ROTULO", default="Entrar com a conta Microsoft institucional"),
}
# Login por usuário e senha do próprio Nexo (contas locais). Pode ser desligado quando o login institucional
# estiver em uso; administradores de suporte continuam no admin do Django, se habilitado.
NEXO_LOGIN_LOCAL = env.bool("NEXO_LOGIN_LOCAL", default=True)

# E-mail e credenciais (ADR-018). Sem NEXO_EMAIL_HOST, nada é enviado: a senha gerada aparece só na tela
# de quem cadastrou, para ser entregue por outro meio.
NEXO_EMAIL_HOST = env("NEXO_EMAIL_HOST", default="")
if NEXO_EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = NEXO_EMAIL_HOST
    EMAIL_PORT = env.int("NEXO_EMAIL_PORTA", default=587)
    EMAIL_HOST_USER = env("NEXO_EMAIL_USUARIO", default="")
    EMAIL_HOST_PASSWORD = env("NEXO_EMAIL_SENHA", default="")
    EMAIL_USE_TLS = env.bool("NEXO_EMAIL_TLS", default=True)
    EMAIL_USE_SSL = env.bool("NEXO_EMAIL_SSL", default=False)
    EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = env("NEXO_EMAIL_REMETENTE", default="nexo@localhost")
NEXO_CREDENCIAIS = {
    # Endereço do Nexo que vai no e-mail (ex.: https://nexo.exemplo). Vazio = endereço da própria requisição.
    "URL_PUBLICA": env("NEXO_URL_PUBLICA", default=""),
    "VALIDADE_HORAS": env.int("NEXO_SENHA_TEMPORARIA_HORAS", default=72),
}

# Revisão periódica de documentos (ADR-015)
NEXO_REVISAO = {
    "ANTECEDENCIA_DIAS": env.int("NEXO_REVISAO_ANTECEDENCIA_DIAS", default=30),
    "REPETIR_DIAS": env.int("NEXO_REVISAO_REPETIR_DIAS", default=7),
}

# Cópias de segurança (banco + arquivos) — ADR-011 e docs/architecture/copia-de-seguranca.md.
NEXO_BACKUP = {
    "DIR": Path(env("NEXO_BACKUP_DIR", default=str(BASE_DIR / "copias"))),
    # Senha que cifra as cópias (AES-256-GCM). Guarde-a FORA do servidor: sem ela a cópia não abre.
    "SENHA": env("NEXO_BACKUP_SENHA", default=""),
    "EXIGIR_SENHA": env.bool("NEXO_BACKUP_EXIGIR_SENHA", default=not DEBUG),
    "RETENCAO": env.int("NEXO_BACKUP_RETENCAO", default=14),
    # Pasta do pg_dump/pg_restore/psql, se não estiverem no PATH
    "PG_BIN": env("NEXO_PG_BIN", default=""),
    # Idade máxima (horas) da última cópia antes de o painel alertar
    "ALERTA_HORAS": env.int("NEXO_BACKUP_ALERTA_HORAS", default=30),
}

NEXO_INGESTAO = {
    "TAMANHO_TRECHO": env.int("NEXO_TAMANHO_TRECHO", default=1200),
    "SOBREPOSICAO": env.int("NEXO_SOBREPOSICAO_TRECHO", default=200),
    # Processa a fila na própria requisição (útil em instalação local de um usuário).
    "PROCESSAR_IMEDIATAMENTE": env.bool("NEXO_PROCESSAR_IMEDIATAMENTE", default=False),
}

# --------------------------------------------------------------------------
# Logs
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simples": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simples"}},
    "root": {"handlers": ["console"], "level": env("NEXO_LOG_NIVEL", default="INFO")},
}
