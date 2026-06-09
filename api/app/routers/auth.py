"""
Endpoints de autenticación.

- POST /auth/register : registro de un nuevo jugador.
- POST /auth/login    : inicia sesión y devuelve un JWT.
- GET  /auth/me       : datos del usuario autenticado (ruta protegida).
- GET  /auth/admin-test : ejemplo de ruta restringida por rol.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user, require_roles
from app.schemas import CambioPassword, LoginRequest, RegistroUsuario, Token, UsuarioOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter()

# Rol por defecto al auto-registrarse desde la app móvil.
# Entrenadores, árbitros y superadmin los crea un administrador.
ROL_POR_DEFECTO = "jugador"


@router.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registrar(datos: RegistroUsuario, db: Session = Depends(get_db)):
    # ¿Correo ya usado?
    if db.query(models.Usuario).filter_by(correo=datos.correo).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    rol = db.query(models.Rol).filter_by(nombre=ROL_POR_DEFECTO).first()
    if rol is None:
        raise HTTPException(
            status_code=500,
            detail="Faltan los roles base. Ejecuta el seed: python -m app.seed",
        )

    usuario = models.Usuario(
        rol_id=rol.id,
        nombre=datos.nombre,
        correo=datos.correo,
        password_hash=hash_password(datos.password),  # se guarda el hash, no la contraseña
        telefono=datos.telefono,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    # UsuarioOut espera un campo 'rol' como texto
    return UsuarioOut(
        id=usuario.id, nombre=usuario.nombre, correo=usuario.correo,
        rol=rol.nombre, activo=usuario.activo,
    )


@router.post("/login", response_model=Token)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter_by(correo=datos.correo).first()

    # Mismo mensaje para correo inexistente o contraseña incorrecta:
    # no revelar cuál de los dos falló.
    if usuario is None or not verify_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="La cuenta está desactivada")

    token = create_access_token(usuario_id=usuario.id, rol=usuario.rol.nombre)
    return Token(access_token=token, debe_cambiar_password=usuario.debe_cambiar_password)


@router.get("/me", response_model=UsuarioOut)
def yo(usuario: models.Usuario = Depends(get_current_user)):
    return UsuarioOut(
        id=usuario.id, nombre=usuario.nombre, correo=usuario.correo,
        rol=usuario.rol.nombre, activo=usuario.activo,
    )


@router.post("/cambiar-password")
def cambiar_password(
    datos: CambioPassword,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Cambia la contraseña del usuario autenticado y limpia la marca de cambio obligatorio."""
    if not verify_password(datos.password_actual, usuario.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    usuario.password_hash = hash_password(datos.password_nueva)
    usuario.debe_cambiar_password = False
    db.commit()
    return {"mensaje": "Contraseña actualizada"}


@router.get("/admin-test")
def solo_admin(usuario: models.Usuario = Depends(require_roles("superadmin"))):
    """Ejemplo: solo accesible por el superadmin. Así se protege cualquier ruta."""
    return {"mensaje": f"Hola {usuario.nombre}, tienes acceso de administrador."}
