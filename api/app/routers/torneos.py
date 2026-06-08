"""
CRUD de Torneos — primera rebanada vertical completa.

Sirve de PLANTILLA para los demás módulos (reservas, equipos, partidos):
muestra el patrón de listar/ver (cualquier usuario autenticado) y
crear/editar/eliminar (solo superadmin).

Reglas de acceso:
- Consultar (GET): cualquier usuario autenticado.
- Crear/editar/eliminar: solo 'superadmin'.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user, require_roles
from app.schemas import TorneoCreate, TorneoOut, TorneoUpdate

router = APIRouter()


def _obtener_torneo(db: Session, torneo_id: int) -> models.Torneo:
    torneo = db.get(models.Torneo, torneo_id)
    if torneo is None:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return torneo


# ---------- Lectura (cualquier usuario autenticado) ----------
@router.get("", response_model=list[TorneoOut])
def listar_torneos(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    consulta = db.query(models.Torneo)
    if estado:
        consulta = consulta.filter(models.Torneo.estado == estado)
    return consulta.order_by(models.Torneo.id).all()


@router.get("/{torneo_id}", response_model=TorneoOut)
def ver_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    return _obtener_torneo(db, torneo_id)


# ---------- Escritura (solo superadmin) ----------
@router.post("", response_model=TorneoOut, status_code=status.HTTP_201_CREATED)
def crear_torneo(
    datos: TorneoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    # La sede referenciada debe existir
    if db.get(models.Sede, datos.sede_id) is None:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")

    torneo = models.Torneo(**datos.model_dump())
    db.add(torneo)
    db.commit()
    db.refresh(torneo)
    return torneo


@router.put("/{torneo_id}", response_model=TorneoOut)
def actualizar_torneo(
    torneo_id: int,
    datos: TorneoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)

    cambios = datos.model_dump(exclude_unset=True)  # solo lo que se envió
    if "sede_id" in cambios and db.get(models.Sede, cambios["sede_id"]) is None:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")

    for campo, valor in cambios.items():
        setattr(torneo, campo, valor)

    db.commit()
    db.refresh(torneo)
    return torneo


@router.delete("/{torneo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    torneo = _obtener_torneo(db, torneo_id)
    db.delete(torneo)
    db.commit()
    # 204: sin cuerpo de respuesta
