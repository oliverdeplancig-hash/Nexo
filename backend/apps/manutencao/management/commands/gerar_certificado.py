"""Gera certificado autoassinado para o HTTPS do servidor de rede no Windows (ADR-019).

    python manage.py gerar_certificado [--nome nexo.unidade.local] [--ip 10.0.0.5] [--pasta .certificados]

Use quando a TI ainda não forneceu um certificado da instituição. Gera:
  nexo.key  chave privada (fica só no servidor)
  nexo.crt  certificado usado pelo Nexo
  nexo.cer  o mesmo certificado, para a TI distribuir aos computadores da rede (evita o aviso do navegador)
"""

import ipaddress
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from django.conf import settings
from django.core.management.base import BaseCommand


def enderecos_locais() -> list[str]:
    ips = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ips)


class Command(BaseCommand):
    help = "Gera certificado autoassinado (HTTPS) com o nome e os IPs deste computador."

    def add_arguments(self, parser):
        parser.add_argument("--nome", action="append", default=[], help="Nome adicional (pode repetir).")
        parser.add_argument("--ip", action="append", default=[], help="IP adicional (pode repetir).")
        parser.add_argument("--pasta", default=str(Path(settings.BASE_DIR) / ".certificados"))
        parser.add_argument("--dias", type=int, default=825)
        parser.add_argument("--substituir", action="store_true")

    def handle(self, *args, nome, ip, pasta, dias, substituir=False, **opcoes):
        destino = Path(pasta)
        destino.mkdir(parents=True, exist_ok=True)
        chave_arq, crt_arq, cer_arq = destino / "nexo.key", destino / "nexo.crt", destino / "nexo.cer"
        if crt_arq.exists() and not substituir:
            self.stdout.write(f"Certificado já existe em {crt_arq} (use --substituir para gerar outro).")
            return
        maquina = socket.gethostname()
        nomes = list(dict.fromkeys([maquina, socket.getfqdn(), "localhost", *nome]))
        ips = list(dict.fromkeys([*enderecos_locais(), *ip]))
        chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        sujeito = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, nomes[0]), x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Nexo")]
        )
        agora = datetime.now(UTC)
        alternativos = [x509.DNSName(n) for n in nomes if n] + [x509.IPAddress(ipaddress.ip_address(i)) for i in ips]
        certificado = (
            x509.CertificateBuilder()
            .subject_name(sujeito)
            .issuer_name(sujeito)
            .public_key(chave.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(agora - timedelta(minutes=5))
            .not_valid_after(agora + timedelta(days=dias))
            .add_extension(x509.SubjectAlternativeName(alternativos), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(chave, hashes.SHA256())
        )
        chave_arq.write_bytes(
            chave.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()
            )
        )
        crt_arq.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
        cer_arq.write_bytes(certificado.public_bytes(serialization.Encoding.DER))
        self.stdout.write(self.style.SUCCESS(f"Certificado gerado em {destino}"))
        self.stdout.write(f"Nomes: {', '.join(nomes)} | IPs: {', '.join(ips)} | válido por {dias} dias")
        self.stdout.write(
            f"Para os computadores da rede confiarem: distribua {cer_arq} (a TI pode usar política de grupo)."
        )
