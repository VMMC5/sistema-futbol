"""
Envío de correo.

Si hay variables SMTP configuradas en el entorno, envía un correo real.
Si NO las hay (caso típico en desarrollo), registra el correo en la consola,
de modo que el flujo completo funcione sin credenciales.

Variables de entorno (opcionales):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
"""
import os
import smtplib
from email.message import EmailMessage


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
    with smtplib.SMTP(host, puerto) as servidor:
        servidor.starttls()
        usuario = os.getenv("SMTP_USER")
        if usuario:
            servidor.login(usuario, os.getenv("SMTP_PASSWORD", ""))
        servidor.send_message(mensaje)
