"""Validación de datos de tarjeta en PagoCreate."""
import pytest
from pydantic import ValidationError

from app.schemas import PagoCreate


def _tarjeta(**over):
    base = {"numero": "4111111111111111", "exp_mes": 12, "exp_anio": 2999,
            "cvv": "123", "titular": "Ana Perez"}
    base.update(over)
    return base


def test_tarjeta_valida():
    p = PagoCreate(metodo="tarjeta", tarjeta=_tarjeta())
    assert p.tarjeta.numero == "4111111111111111"


def test_tarjeta_requerida_si_metodo_tarjeta():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=None)


def test_numero_no_numerico_falla():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=_tarjeta(numero="41111abc1111"))


def test_cvv_de_2_digitos_falla():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=_tarjeta(cvv="12"))


def test_expiracion_pasada_falla():
    with pytest.raises(ValidationError):
        PagoCreate(metodo="tarjeta", tarjeta=_tarjeta(exp_mes=1, exp_anio=2000))


def test_transferencia_no_requiere_tarjeta():
    p = PagoCreate(metodo="transferencia")
    assert p.tarjeta is None
