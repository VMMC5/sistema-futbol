"""
Envío de correo.

Si hay variables SMTP configuradas en el entorno, envía un correo real.
Si NO las hay (caso típico en desarrollo), registra el correo en la consola,
de modo que el flujo completo funcione sin credenciales.

Variables de entorno (opcionales):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
"""
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

# Segundos máximos esperando al servidor SMTP. Sin esto, un SMTP colgado
# congela la petición (o el background task) indefinidamente.
SMTP_TIMEOUT = 10


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> None:
    host = os.getenv("SMTP_HOST")

    # Sin SMTP configurado -> modo desarrollo: se imprime el correo.
    if not host:
        print("=" * 60)
        print("[CORREO SIMULADO] (configura SMTP_* para envío real)")
        print(f"Para:    {destinatario}")
        print(f"Asunto:  {asunto}")
        print("-" * 60)
        print(cuerpo)
        print("=" * 60)
        return

    mensaje = EmailMessage()
    mensaje["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "no-reply@torneos.app"))
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    puerto = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, puerto, timeout=SMTP_TIMEOUT) as servidor:
        servidor.starttls()
        usuario = os.getenv("SMTP_USER")
        if usuario:
            servidor.login(usuario, os.getenv("SMTP_PASSWORD", ""))
        servidor.send_message(mensaje)


def enviar_correo_seguro(destinatario: str, asunto: str, cuerpo: str) -> None:
    """Variante best-effort para BackgroundTasks: nunca propaga.

    Si el envío falla, el error se loguea SIN el destinatario ni el cuerpo
    (el cuerpo puede llevar una contraseña temporal); la operación que lo
    encoló (p. ej. aceptar una solicitud) ya quedó firme en la BD.
    """
    try:
        enviar_correo(destinatario, asunto, cuerpo)
    except Exception as exc:  # consciente: best-effort, igual que enviar_push
        logger.error("Fallo el envio de correo '%s': %s", asunto, type(exc).__name__)
