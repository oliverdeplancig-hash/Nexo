"""Configurações para a suíte de testes: provedor de IA falso e determinístico."""

from .settings import *  # noqa: F401,F403
from .settings import NEXO_BACKUP, NEXO_IA

NEXO_IA = {**NEXO_IA, "PROVEDOR": "falso"}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}  # noqa: F405
NEXO_ARMAZENAMENTO_DIR = BASE_DIR / ".armazenamento-testes"  # noqa: F405
NEXO_BACKUP = {**NEXO_BACKUP, "DIR": BASE_DIR / ".copias-testes", "SENHA": "", "EXIGIR_SENHA": False}  # noqa: F405
