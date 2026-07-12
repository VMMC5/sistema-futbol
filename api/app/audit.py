"""
Auditoria de eventos sensibles.

Deja rastro de QUIEN hizo QUE y desde donde, para poder investigar un incidente
despues: intentos de login, cambios de contrasena, confirmacion de pagos, altas
y bajas de usuarios, y resolucion de solicitudes.

REGLA: aqui NUNCA se registran secretos. Ni contrasenas, ni hashes, ni tokens.
Solo identificadores y el resultado de la accion.

Los eventos salen por el logger 'auditoria' con el prefijo AUDIT, asi que se
pueden filtrar en los logs del contenedor:
    docker compose logs api | grep AUDIT
"""
import logging

logger = logging.getLogger("auditoria")

# Nombres de evento, centralizados para no escribirlos sueltos por ahi.
LOGIN_EXITOSO = "login_exitoso"
LOGIN_FALLIDO = "login_fallido"
LOGIN_CUENTA_DESACTIVADA = "login_cuenta_desactivada"
PASSWORD_CAMBIADA = "password_cambiada"
PAGO_CONFIRMADO = "pago_confirmado"
USUARIO_CREADO = "usuario_creado"
# Las bajas se hacen desactivando la cuenta (activo=false), asi que quedan
# cubiertas por USUARIO_ACTUALIZADO: no hay endpoint de borrado.
USUARIO_ACTUALIZADO = "usuario_actualizado"
SOLICITUD_ACEPTADA = "solicitud_aceptada"
SOLICITUD_RECHAZADA = "solicitud_rechazada"


def ip_de(request) -> str:
    """IP de origen de la peticion (o 'desconocida' si no viene)."""
    if request is None or request.client is None:
        return "desconocida"
    return request.client.host


def registrar(evento: str, *, actor_id=None, objetivo=None, ip=None, detalle=None) -> None:
    """Escribe una linea de auditoria.

    actor_id -> usuario que ejecuta la accion (None si aun no se autentico).
    objetivo -> sobre que recae (id de usuario, de pago, correo intentado...).
    """
    partes = [f"AUDIT evento={evento}"]
    if actor_id is not None:
        partes.append(f"actor_id={actor_id}")
    if objetivo is not None:
        partes.append(f"objetivo={objetivo}")
    if ip:
        partes.append(f"ip={ip}")
    if detalle:
        partes.append(f"detalle={detalle}")
    logger.info(" ".join(partes))
