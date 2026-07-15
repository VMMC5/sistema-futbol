"""
Creación de notificaciones y envío push (Expo).

crear_notificacion() es la ÚNICA puerta para crear una notificación (salvo el
seed): inserta la fila en BD y, si se le pasa un BackgroundTasks, encola el
envío push. El envío es best-effort: nunca rompe la acción que lo originó.
"""
import logging

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_TIMEOUT = 10.0


def crear_notificacion(db: Session, usuario_id: int, titulo: str, mensaje: str,
                       background_tasks=None) -> None:
    db.add(models.Notificacion(usuario_id=usuario_id, titulo=titulo, mensaje=mensaje))
    if background_tasks is not None:
        background_tasks.add_task(enviar_push, usuario_id, titulo, mensaje)


def _post_expo(mensajes: list[dict]) -> list[dict]:
    """POST a la Expo Push API. Devuelve la lista 'data' de tickets."""
    with httpx.Client(timeout=_TIMEOUT) as cliente:
        respuesta = cliente.post(EXPO_PUSH_URL, json=mensajes)
        respuesta.raise_for_status()
        return respuesta.json().get("data", [])


def enviar_push(usuario_id: int, titulo: str, mensaje: str) -> None:
    """Tarea de fondo: envía el push a los dispositivos del usuario y purga
    los tokens que Expo reporte como no registrados. Best-effort."""
    db = SessionLocal()
    try:
        dispositivos = db.query(models.DispositivoPush).filter_by(usuario_id=usuario_id).all()
        if not dispositivos:
            return
        mensajes = [
            {"to": d.token, "title": titulo, "body": mensaje, "sound": "default"}
            for d in dispositivos
        ]
        try:
            tickets = _post_expo(mensajes)
        except Exception as exc:
            # best-effort: no rompemos nada si Expo falla, pero lo registramos
            # (sin token ni cuerpo del mensaje) para tener visibilidad en prod.
            logger.warning("Fallo al enviar push (usuario_id=%s): %s", usuario_id, exc)
            return
        for disp, ticket in zip(dispositivos, tickets):
            if (ticket.get("status") == "error"
                    and ticket.get("details", {}).get("error") == "DeviceNotRegistered"):
                db.delete(disp)
        db.commit()
    except Exception:
        logger.warning("Error al purgar tokens push (usuario_id=%s)", usuario_id, exc_info=True)
        db.rollback()
    finally:
        db.close()
