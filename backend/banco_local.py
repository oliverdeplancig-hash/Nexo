"""Sobe o PostgreSQL embutido (pgserver) para uso LOCAL e grava a URL no .env.

Uso: python banco_local.py [iniciar|parar|status]

O servidor fica em backend/.pgdata e continua rodando depois que este script
termina. A porta pode mudar a cada início; por isso a URL é regravada no .env.
"""

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PGDATA = BASE / ".pgdata"
ENV = BASE / ".env"


def gravar_env(chave: str, valor: str) -> None:
    linhas = ENV.read_text(encoding="utf-8-sig").splitlines() if ENV.exists() else []
    padrao = re.compile(rf"^\s*{re.escape(chave)}\s*=")
    novas = [linha for linha in linhas if not padrao.match(linha)]
    novas.append(f"{chave}={valor}")
    ENV.write_text("\n".join(novas) + "\n", encoding="utf-8")


def garantir_fusos_horarios() -> bool:
    """O PostgreSQL do pgserver para Windows vem sem a base de fusos horários,
    e o Django exige o fuso "UTC". Copia a base do pacote `tzdata`. Retorna True se copiou."""
    import shutil

    import pgserver
    import tzdata

    destino = Path(pgserver.__file__).parent / "pginstall" / "share" / "postgresql" / "timezone"
    if (destino / "UTC").exists():
        return False
    origem = Path(tzdata.__file__).parent / "zoneinfo"
    shutil.copytree(origem, destino, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    print("Base de fusos horarios instalada no PostgreSQL local.")
    return True


def parar() -> None:
    import subprocess

    from pgserver._commands import pg_ctl

    if not (PGDATA / "postmaster.pid").exists():
        return
    try:
        pg_ctl(["-w", "-m", "fast", "stop"], pgdata=PGDATA)
    except subprocess.CalledProcessError:
        pass


def main() -> int:
    import pgserver

    acao = sys.argv[1] if len(sys.argv) > 1 else "iniciar"
    if acao == "parar":
        parar()
        print("PostgreSQL local parado.")
        return 0
    if garantir_fusos_horarios():
        parar()  # um servidor já em execução precisa reiniciar para carregar os fusos
    servidor = pgserver.get_server(PGDATA, cleanup_mode=None)
    existe = servidor.psql("SELECT 1 FROM pg_database WHERE datname = 'nexo';")
    if "(1 row)" not in existe and "(1 linha)" not in existe:
        servidor.psql("CREATE DATABASE nexo;")
        print("Banco 'nexo' criado.")
    uri = servidor.get_uri("nexo")
    gravar_env("NEXO_DATABASE_URL", uri)
    print(f"PostgreSQL local em execucao: {uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
