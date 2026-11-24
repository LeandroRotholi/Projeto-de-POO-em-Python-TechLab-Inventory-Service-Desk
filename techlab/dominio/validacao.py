"""Funções auxiliares de validação usadas pelos setters das entidades."""

from __future__ import annotations

import ipaddress
import unicodedata
from datetime import date, datetime
from typing import Any

from techlab.excecoes import DadosInvalidosException


def texto_obrigatorio(valor: Any, campo: str, tamanho_max: int = 200) -> str:
    if valor is None or not str(valor).strip():
        raise DadosInvalidosException(f"O campo '{campo}' é obrigatório.")
    texto = str(valor).strip()
    if len(texto) > tamanho_max:
        raise DadosInvalidosException(
            f"O campo '{campo}' excede {tamanho_max} caracteres."
        )
    return texto


def inteiro_positivo(valor: Any, campo: str) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise DadosInvalidosException(f"O campo '{campo}' deve ser um número inteiro.")
    if numero <= 0:
        raise DadosInvalidosException(f"O campo '{campo}' deve ser maior que zero.")
    return numero


def converter_data(valor: Any, campo: str = "data") -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError:
        raise DadosInvalidosException(
            f"Data inválida em '{campo}': use o formato AAAA-MM-DD."
        )


def converter_datahora(valor: Any, campo: str = "data/hora") -> datetime:
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor).strip())
    except ValueError:
        raise DadosInvalidosException(
            f"Data/hora inválida em '{campo}': use AAAA-MM-DDTHH:MM:SS."
        )


def endereco_ip(valor: Any, campo: str = "ip") -> str:
    try:
        return str(ipaddress.ip_address(str(valor).strip()))
    except ValueError:
        raise DadosInvalidosException(f"Endereço IP inválido em '{campo}': {valor!r}.")


def normalizar(texto: Any) -> str:
    """Remove acentos e converte para maiúsculas (útil para comparar rótulos)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().upper()
