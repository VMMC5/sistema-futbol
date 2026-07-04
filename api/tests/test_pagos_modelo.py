"""El modelo Pago admite concepto, completado_en y expone usuario_nombre."""
from datetime import datetime, timezone

from app import models


def test_pago_admite_concepto_y_completado(db_session):
    db = db_session()
    pago = models.Pago(
        usuario_id=1, monto=200, metodo="tarjeta", estado="completado",
        referencia="MOCK-ABCD1234", concepto="Reserva Cancha 1",
        completado_en=datetime.now(timezone.utc),
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    assert pago.concepto == "Reserva Cancha 1"
    assert pago.completado_en is not None
    assert pago.usuario_nombre == "Admin"   # usuario id=1 es 'Admin' en conftest
