"""
Pagos en línea (pasarela simulada). Paga reservas e inscripciones a torneos.

Reglas de acceso:
- Pagar una reserva: su dueño.
- El monto lo calcula el servidor (nunca el cliente).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, pagos_service
from app.deps import get_current_user
from app.schemas import PagoCreate, PagoOut

router = APIRouter()


def _es_admin(usuario: models.Usuario) -> bool:
    return usuario.rol.nombre == "superadmin"


@router.post("/reserva/{reserva_id}", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def pagar_reserva(
    reserva_id: int,
    datos: PagoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    reserva = db.get(models.Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if not _es_admin(usuario) and reserva.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes pagar una reserva ajena")
    return pagos_service.pagar_reserva(db, usuario, reserva, datos)
