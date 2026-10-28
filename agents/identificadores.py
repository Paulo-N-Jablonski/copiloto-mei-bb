"""
Módulo de geração e validação canônica de identificadores do sistema.

Padrão canônico de recibo:  ^REC-[0-9A-F]{8}$
Exemplos válidos: REC-2898A06A, REC-AABBCCDD, REC-00000000

A entropia é gerada exclusivamente no servidor (uuid4), desacoplada
de qualquer dado arbitrário fornecido pelo cliente.
"""

from __future__ import annotations

import re
import uuid

# Regex canônico — compartilhado pelo Pydantic Field(pattern=...) e pelos testes
RECIBO_ID_PATTERN: str = r"^REC-[0-9A-F]{8}$"
_RECIBO_RE = re.compile(RECIBO_ID_PATTERN)


def gerar_recibo_id() -> str:
    """
    Gera um identificador de recibo canônico com entropia UUID4.

    Returns:
        str: Identificador no formato ``REC-XXXXXXXX`` onde X é dígito hexadecimal
             maiúsculo (ex: ``REC-2898A06A``).
    """
    return f"REC-{uuid.uuid4().hex[:8].upper()}"


def recibo_id_valido(valor: str) -> bool:
    """
    Valida se uma string está no formato canônico ``^REC-[0-9A-F]{8}$``.

    Args:
        valor: String a ser validada.

    Returns:
        bool: ``True`` se o formato for canônico, ``False`` caso contrário.
    """
    return bool(_RECIBO_RE.fullmatch(valor))
