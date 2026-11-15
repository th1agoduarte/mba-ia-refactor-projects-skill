"""Validadores reutilizáveis. Levantam ValidationError (400) com a mensagem do contrato."""

from src.errors import ValidationError


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def exigir_objeto(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def texto(dados, campo, padrao=""):
    valor = dados.get(campo, padrao)
    return valor if isinstance(valor, str) else padrao


def numero_opcional(valor, campo):
    """Converte parâmetro de query string em float; vazio/ausente = None."""
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"Parâmetro {campo} inválido") from None
