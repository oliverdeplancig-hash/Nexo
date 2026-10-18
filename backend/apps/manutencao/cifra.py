"""Criptografia em fluxo das cópias de segurança (AES-256-GCM em blocos de 1 MiB).

Formato:
    CABEÇALHO = "NEXOBK1\\0" (8) | sal (16) | prefixo do nonce (8)
    BLOCO     = tamanho do texto cifrado (4, big-endian) | texto cifrado + etiqueta GCM (16)

- Chave derivada da senha com scrypt (n=2^15, r=8, p=1) e o sal do cabeçalho.
- Nonce de cada bloco = prefixo (8) + número do bloco (4): nunca se repete no mesmo arquivo.
- Dados associados (AAD) = cabeçalho + número do bloco + marca de último bloco: blocos trocados de
  lugar, removidos ou um arquivo cortado no meio são detectados (o último bloco é obrigatório).
Assim a cópia pode ser gravada e lida sem caber inteira na memória.
"""

from __future__ import annotations

import hashlib
import io
import os
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGICA = b"NEXOBK1\x00"
TAMANHO_BLOCO = 1024 * 1024
_CABECALHO = len(MAGICA) + 16 + 8


class ErroCifra(Exception):
    pass


def esta_cifrado(caminho) -> bool:
    with open(caminho, "rb") as f:
        return f.read(len(MAGICA)) == MAGICA


def _chave(senha: str, sal: bytes) -> bytes:
    if not senha:
        raise ErroCifra("Senha da cópia de segurança vazia.")
    return hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def _aad(cabecalho: bytes, indice: int, ultimo: bool) -> bytes:
    return cabecalho + struct.pack(">IB", indice, 1 if ultimo else 0)


class EscritorCifrado(io.RawIOBase):
    """Arquivo somente-escrita que cifra o que recebe. `close()` grava o último bloco."""

    def __init__(self, destino, senha: str):
        super().__init__()
        self._destino = destino
        sal = os.urandom(16)
        self._prefixo = os.urandom(8)
        self._cabecalho = MAGICA + sal + self._prefixo
        self._aes = AESGCM(_chave(senha, sal))
        self._buffer = bytearray()
        self._indice = 0
        destino.write(self._cabecalho)

    def writable(self):
        return True

    def write(self, dados) -> int:
        self._buffer += dados
        while len(self._buffer) > TAMANHO_BLOCO:
            self._gravar(bytes(self._buffer[:TAMANHO_BLOCO]), ultimo=False)
            del self._buffer[:TAMANHO_BLOCO]
        return len(dados)

    def _gravar(self, claro: bytes, ultimo: bool):
        if self._indice >= 2**32 - 1:
            raise ErroCifra("Cópia grande demais para um único arquivo.")
        nonce = self._prefixo + struct.pack(">I", self._indice)
        cifrado = self._aes.encrypt(nonce, claro, _aad(self._cabecalho, self._indice, ultimo))
        self._destino.write(struct.pack(">I", len(cifrado)) + cifrado)
        self._indice += 1

    def close(self):
        if not self.closed:
            self._gravar(bytes(self._buffer), ultimo=True)
            self._buffer.clear()
            self._destino.flush()
        super().close()


class LeitorCifrado(io.RawIOBase):
    """Arquivo somente-leitura que decifra e confere cada bloco ao ler."""

    def __init__(self, origem, senha: str):
        super().__init__()
        self._origem = origem
        cabecalho = origem.read(_CABECALHO)
        if len(cabecalho) != _CABECALHO or not cabecalho.startswith(MAGICA):
            raise ErroCifra("O arquivo não é uma cópia de segurança cifrada do Nexo.")
        self._cabecalho = cabecalho
        self._prefixo = cabecalho[-8:]
        self._aes = AESGCM(_chave(senha, cabecalho[len(MAGICA) : len(MAGICA) + 16]))
        self._buffer = b""
        self._pos = 0
        self._indice = 0
        self._fim = False

    def readable(self):
        return True

    def _proximo_bloco(self) -> bool:
        if self._fim:
            return False
        tamanho_bruto = self._origem.read(4)
        if len(tamanho_bruto) < 4:
            raise ErroCifra("Cópia de segurança incompleta (arquivo cortado).")
        (tamanho,) = struct.unpack(">I", tamanho_bruto)
        if tamanho > TAMANHO_BLOCO + 16:
            raise ErroCifra("Cópia de segurança corrompida.")
        cifrado = self._origem.read(tamanho)
        if len(cifrado) < tamanho:
            raise ErroCifra("Cópia de segurança incompleta (arquivo cortado).")
        nonce = self._prefixo + struct.pack(">I", self._indice)
        for ultimo in (False, True):
            try:
                claro = self._aes.decrypt(nonce, cifrado, _aad(self._cabecalho, self._indice, ultimo))
                break
            except InvalidTag:
                continue
        else:
            if self._indice == 0:
                raise ErroCifra("Senha incorreta ou cópia de segurança corrompida.")
            raise ErroCifra(f"Cópia de segurança corrompida (bloco {self._indice}).")
        self._indice += 1
        self._buffer, self._pos = claro, 0
        if ultimo:
            self._fim = True
            if self._origem.read(1):
                raise ErroCifra("Dados extras depois do fim da cópia de segurança.")
        return True

    def readinto(self, destino) -> int:
        while self._pos >= len(self._buffer) and self._proximo_bloco():
            pass
        n = min(len(destino), len(self._buffer) - self._pos)
        destino[:n] = self._buffer[self._pos : self._pos + n]
        self._pos += n
        return n
