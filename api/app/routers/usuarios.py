"""
Gestión de usuarios — solo para el superadmin.

Permite dar de alta usuarios con cualquier rol (entrenadores, árbitros, etc.),
listarlos, editarlos y activarlos/desactivarios. Los usuarios NO se eliminan
(están referenciados por muchas tablas): se desactivan poniendo activo=False,
y el login rechaza las cuentas inactivas.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import audit, models
from app.deps import get_current_user, require_roles
from app.schemas import UsuarioAdminCreate, UsuarioAdminOut, UsuarioAdminUpdate
from app.security import hash_password

router = APIRouter()


def _to_out(u: models.Usuario) -> UsuarioAdminOut:
    return UsuarioAdminOut(
        id=u.id, nombre=u.nombre, correo=u.correo,
        rol=u.rol.nombre, telefono=u.telefono, activo=u.activo,
    )


def _rol_o_400(db: Session, nombre_rol: str) -> models.Rol:
    rol = db.query(models.Rol).filter_by(nombre=nombre_rol).first()
    if rol is None:
        raise HTTPException(status_code=400, detail=f"El rol '{nombre_rol}' no existe")
    return rol


@router.get("/roles", response_model=list[str])
def listar_roles(
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    return [r.nombre for r in db.query(models.Rol).order_by(models.Rol.nombre).all()]


@router.get("", response_model=list[UsuarioAdminOut])
def listar_usuarios(
    rol: str | None = None,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    consulta = db.query(models.Usuario)
    if rol:
        consulta = consulta.join(models.Rol).filter(models.Rol.nombre == rol)
    return [_to_out(u) for u in consulta.order_by(models.Usuario.nombre).all()]


@router.get("/{usuario_id}", response_model=UsuarioAdminOut)
def ver_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    usuario = db.get(models.Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _to_out(usuario)


@router.post("", response_model=UsuarioAdminOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioAdminCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    if db.query(models.Usuario).filter_by(correo=datos.correo).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    rol = _rol_o_400(db, datos.rol)
    usuario = models.Usuario(
        rol_id=rol.id,
        nombre=datos.nombre,
        correo=datos.correo,
        password_hash=hash_password(datos.password),
        telefono=datos.telefono,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    audit.registrar(
        audit.USUARIO_CREADO, actor_id=_admin.id, objetivo=usuario.id,
        detalle=f"rol={rol.nombre}",
    )
    return _to_out(usuario)


@router.put("/{usuario_id}", response_model=UsuarioAdminOut)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioAdminUpdate,
    db: Session = Depends(get_db),
    admin: models.Usuario = Depends(require_roles("superadmin")),
):
    usuario = db.get(models.Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cambios = datos.model_dump(exclude_unset=True)

    # Un admin no puede desactivarse a sí mismo (evita quedar fuera del sistema)
    if cambios.get("activo") is False and usuario.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")

    if "rol" in cambios and cambios["rol"] is not None:
        usuario.rol_id = _rol_o_400(db, cambios["rol"]).id
    if "password" in cambios and cambios["password"]:
        usuario.password_hash = hash_password(cambios["password"])
    if "nombre" in cambios and cambios["nombre"] is not None:
        usuario.nombre = cambios["nombre"]
    if "telefono" in cambios:
        usuario.telefono = cambios["telefono"]
    if "activo" in cambios and cambios["activo"] is not None:
        usuario.activo = cambios["activo"]

    db.commit()
    db.refresh(usuario)
    # Solo los NOMBRES de los campos tocados: 'cambios' lleva la contraseña en
    # claro y esa no debe acabar nunca en los logs.
    audit.registrar(
        audit.USUARIO_ACTUALIZADO, actor_id=admin.id, objetivo=usuario.id,
        detalle=f"campos={','.join(sorted(cambios))}",
    )
    return _to_out(usuario)
