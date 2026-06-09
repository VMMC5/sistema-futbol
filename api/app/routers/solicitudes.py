"""
Solicitudes de registro de entrenador / árbitro.

Flujo:
1. La persona envía una solicitud (público) con sus datos y un documento
   (PDF o imagen) que acredita que es entrenador/árbitro oficial.
2. El administrador revisa el documento y acepta o rechaza.
3. Al ACEPTAR: se crea el usuario con una contraseña temporal y la marca
   'debe_cambiar_password', y se le envía un correo con sus credenciales.
"""
import os
import secrets
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import require_roles
from app.email_utils import enviar_correo
from app.schemas import RechazoSolicitud, SolicitudOut
from app.security import hash_password

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/code/uploads")
TIPOS_PERMITIDOS = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
ROLES_VALIDOS = {"entrenador", "arbitro"}


@router.post("", response_model=SolicitudOut, status_code=status.HTTP_201_CREATED)
async def crear_solicitud(
    nombre: str = Form(..., min_length=2, max_length=80),
    correo: str = Form(...),
    rol_solicitado: str = Form(...),
    telefono: str | None = Form(None),
    documento: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """PÚBLICO: envía una solicitud con el documento de acreditación."""
    if rol_solicitado not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="El rol debe ser 'entrenador' o 'arbitro'")

    # El correo no debe pertenecer ya a un usuario
    if db.query(models.Usuario).filter_by(correo=correo).first():
        raise HTTPException(status_code=400, detail="Ese correo ya tiene una cuenta")

    # Ni tener una solicitud pendiente
    pendiente = (
        db.query(models.SolicitudRegistro)
        .filter_by(correo=correo, estado="pendiente")
        .first()
    )
    if pendiente:
        raise HTTPException(status_code=400, detail="Ya existe una solicitud pendiente con ese correo")

    # Validar el documento
    if documento.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail="El documento debe ser PDF, PNG o JPG")
    contenido = await documento.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="El documento supera el tamaño máximo (5 MB)")

    # Guardar el archivo con un nombre único y seguro
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    extension = TIPOS_PERMITIDOS[documento.content_type]
    nombre_archivo = f"{uuid.uuid4().hex}{extension}"
    with open(os.path.join(UPLOAD_DIR, nombre_archivo), "wb") as f:
        f.write(contenido)

    solicitud = models.SolicitudRegistro(
        nombre=nombre, correo=correo, telefono=telefono,
        rol_solicitado=rol_solicitado, documento_nombre=nombre_archivo, estado="pendiente",
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return solicitud


@router.get("", response_model=list[SolicitudOut])
def listar_solicitudes(
    estado: str = "pendiente",
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    return (
        db.query(models.SolicitudRegistro)
        .filter(models.SolicitudRegistro.estado == estado)
        .order_by(models.SolicitudRegistro.creada_en.desc())
        .all()
    )


@router.get("/{solicitud_id}/documento")
def ver_documento(
    solicitud_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    solicitud = db.get(models.SolicitudRegistro, solicitud_id)
    if solicitud is None or not solicitud.documento_nombre:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    ruta = os.path.join(UPLOAD_DIR, solicitud.documento_nombre)
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")
    return FileResponse(ruta)


@router.post("/{solicitud_id}/aceptar", response_model=SolicitudOut)
def aceptar_solicitud(
    solicitud_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    solicitud = db.get(models.SolicitudRegistro, solicitud_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La solicitud ya fue procesada")
    if db.query(models.Usuario).filter_by(correo=solicitud.correo).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")

    rol = db.query(models.Rol).filter_by(nombre=solicitud.rol_solicitado).first()
    if rol is None:
        raise HTTPException(status_code=400, detail="El rol solicitado no existe")

    # Contraseña temporal aleatoria; el usuario deberá cambiarla al entrar
    password_temporal = secrets.token_urlsafe(9)
    usuario = models.Usuario(
        rol_id=rol.id,
        nombre=solicitud.nombre,
        correo=solicitud.correo,
        telefono=solicitud.telefono,
        password_hash=hash_password(password_temporal),
        debe_cambiar_password=True,
    )
    db.add(usuario)
    solicitud.estado = "aceptada"
    db.commit()

    # Correo con las credenciales temporales
    enviar_correo(
        destinatario=solicitud.correo,
        asunto="Tu cuenta en el Sistema de Torneos ha sido aprobada",
        cuerpo=(
            f"Hola {solicitud.nombre},\n\n"
            f"Tu solicitud como {solicitud.rol_solicitado} fue aprobada.\n\n"
            f"Para iniciar sesión en la app usa:\n"
            f"  Correo: {solicitud.correo}\n"
            f"  Contraseña temporal: {password_temporal}\n\n"
            f"Por seguridad, el sistema te pedirá cambiar esta contraseña "
            f"la primera vez que inicies sesión.\n\n"
            f"Saludos,\nEquipo de Torneos"
        ),
    )
    db.refresh(solicitud)
    return solicitud


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudOut)
def rechazar_solicitud(
    solicitud_id: int,
    datos: RechazoSolicitud,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(require_roles("superadmin")),
):
    solicitud = db.get(models.SolicitudRegistro, solicitud_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La solicitud ya fue procesada")

    solicitud.estado = "rechazada"
    solicitud.motivo = datos.motivo
    db.commit()

    enviar_correo(
        destinatario=solicitud.correo,
        asunto="Sobre tu solicitud en el Sistema de Torneos",
        cuerpo=(
            f"Hola {solicitud.nombre},\n\n"
            f"Lamentamos informarte que tu solicitud no fue aprobada en esta ocasión."
            + (f"\nMotivo: {datos.motivo}" if datos.motivo else "")
            + "\n\nSaludos,\nEquipo de Torneos"
        ),
    )
    db.refresh(solicitud)
    return solicitud
