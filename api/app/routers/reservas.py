"""
Reservas de canchas.

Lo interesante de este módulo es la REGLA DE NEGOCIO: no se puede reservar una
cancha en un horario que se solape con otra reserva activa de la misma cancha
ese mismo día. También muestra el patrón de "propiedad": un usuario solo ve y
gestiona sus propias reservas; el superadmin las ve todas.

Reglas de acceso:
- Crear / ver lo propio: cualquier usuario autenticado (la reserva queda a su nombre).
- Ver todas / confirmar: solo 'superadmin'.
- Cancelar: el dueño de la reserva o el superadmin.

Sobre el pago: la reserva nace en estado 'pendiente'. La vinculación con el
pago (campo pago_id, relación 1:1) y el paso a 'confirmada' se harán cuando se
integre el módulo de pagos. Aquí queda el hueco preparado.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user, require_roles
from app.schemas import ReservaCreate, ReservaOut

router = APIRouter()


def _es_admin(usuario: models.Usuario) -> bool:
    return usuario.rol.nombre == "superadmin"


def _obtener_reserva(db: Session, reserva_id: int) -> models.Reserva:
    reserva = db.get(models.Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


def _hay_solapamiento(db: Session, cancha_id: int, fecha, hora_inicio, hora_fin) -> bool:
    """
    Dos intervalos [inicio, fin) se solapan si:  inicio_a < fin_b  Y  inicio_b < fin_a.
    Se ignoran las reservas canceladas.
    """
    conflicto = (
        db.query(models.Reserva)
        .filter(
            models.Reserva.cancha_id == cancha_id,
            models.Reserva.fecha == fecha,
            models.Reserva.estado != "cancelada",
            models.Reserva.hora_inicio < hora_fin,
            models.Reserva.hora_fin > hora_inicio,
        )
        .first()
    )
    return conflicto is not None


# ---------- Crear (usuario autenticado, a su propio nombre) ----------
@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def crear_reserva(
    datos: ReservaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    cancha = db.get(models.Cancha, datos.cancha_id)
    if cancha is None:
        raise HTTPException(status_code=400, detail="La cancha indicada no existe")
    if not cancha.disponible:
        raise HTTPException(status_code=400, detail="La cancha no está disponible")

    if _hay_solapamiento(db, datos.cancha_id, datos.fecha, datos.hora_inicio, datos.hora_fin):
        # 409 Conflict: el horario choca con otra reserva
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una reserva para esa cancha en ese horario",
        )

    reserva = models.Reserva(
        usuario_id=usuario.id,            # del token, no del cuerpo
        cancha_id=datos.cancha_id,
        fecha=datos.fecha,
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
        estado="pendiente",
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return reserva


# ---------- Listar ----------
@router.get("", response_model=list[ReservaOut])
def listar_reservas(
    cancha_id: int | None = None,
    fecha: date | None = None,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Reserva).options(*models.CARGA_RESERVA)

    # Un usuario normal solo ve SUS reservas; el admin las ve todas.
    if not _es_admin(usuario):
        consulta = consulta.filter(models.Reserva.usuario_id == usuario.id)

    if cancha_id:
        consulta = consulta.filter(models.Reserva.cancha_id == cancha_id)
    if fecha:
        consulta = consulta.filter(models.Reserva.fecha == fecha)

    return consulta.order_by(models.Reserva.fecha, models.Reserva.hora_inicio).all()


# ---------- Ver una (dueño o admin) ----------
@router.get("/{reserva_id}", response_model=ReservaOut)
def ver_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    reserva = _obtener_reserva(db, reserva_id)
    if not _es_admin(usuario) and reserva.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes ver una reserva ajena")
    return reserva


# ---------- Cancelar (dueño o admin) ----------
@router.post("/{reserva_id}/cancelar", response_model=ReservaOut)
def cancelar_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    reserva = _obtener_reserva(db, reserva_id)
    if not _es_admin(usuario) and reserva.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes cancelar una reserva ajena")

    reserva.estado = "cancelada"
    db.commit()
    db.refresh(reserva)
    return reserva


# ---------- Confirmar (solo admin; tras el pago, más adelante) ----------
@router.post("/{reserva_id}/confirmar", response_model=ReservaOut)
def confirmar_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    reserva = _obtener_reserva(db, reserva_id)
    reserva.estado = "confirmada"
    db.commit()
    db.refresh(reserva)
    return reserva
