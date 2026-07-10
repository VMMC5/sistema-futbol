"""
Rate limiting (limitacion de peticiones) para frenar ataques de fuerza bruta.

Se usa slowapi con almacenamiento en memoria, limitando por IP de origen. El
caso principal es /auth/login: sin un tope, un atacante puede probar miles de
contrasenas. Aqui NO se hace lockout por cuenta (eso requeriria estado en BD);
es una defensa por IP, simple y sin cambios de esquema.

Configurable por entorno:
  RATE_LIMIT_ENABLED  -> "false" lo desactiva (los tests lo apagan para no
                         acumular contadores entre pruebas). Por defecto activo.
  LOGIN_RATE_LIMIT    -> tope de intentos de login por IP. Por defecto "20/minute"
                         (holgado para no molestar a usuarios legítimos tras un
                         NAT compartido, pero suficiente contra fuerza bruta).
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")

LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "20/minute")

limiter = Limiter(key_func=get_remote_address, enabled=_enabled)
