"""
Pasarela de pago simulada (mock).

No cobra dinero real: decide de forma DETERMINISTA para poder demostrar y
probar los dos caminos. Sustituir MockGateway por un StripeGateway que
implemente la misma interfaz es todo lo que hará falta para pagos reales.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4


@dataclass
class ResultadoCobro:
    estado: str            # "completado" | "fallido" | "pendiente"
    referencia: str
    motivo: str | None = None


class PaymentGateway:
    def charge(self, monto: Decimal, metodo: str, datos_tarjeta: dict | None) -> ResultadoCobro:
        raise NotImplementedError


class MockGateway(PaymentGateway):
    """- tarjeta: aprueba, salvo que el número termine en 0000 (fondos insuficientes).
       - transferencia: queda pendiente hasta que el superadmin la confirme."""

    def charge(self, monto: Decimal, metodo: str, datos_tarjeta: dict | None) -> ResultadoCobro:
        folio = uuid4().hex[:8].upper()
        if metodo == "transferencia":
            return ResultadoCobro(estado="pendiente", referencia=f"TRF-{folio}")

        # tarjeta
        numero = (datos_tarjeta or {}).get("numero", "")
        ultimos4 = numero[-4:]
        if ultimos4 == "0000":
            return ResultadoCobro(estado="fallido", referencia=f"MOCK-{folio}",
                                  motivo="Tarjeta rechazada (fondos insuficientes)")
        return ResultadoCobro(estado="completado", referencia=f"MOCK-{folio}·{ultimos4}")
