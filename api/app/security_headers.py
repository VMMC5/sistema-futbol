"""
Cabeceras de seguridad HTTP para las respuestas de la API.

Son defensas del lado del navegador: impiden que la respuesta se interprete con
un tipo distinto al declarado (nosniff), que la API se embeba en un iframe
ajeno (clickjacking) o que se filtre la URL en el Referer.

La CSP va en dos sabores:
  - Endpoints normales: devuelven JSON, asi que no necesitan cargar NADA
    ('none' en todo). Es la politica mas estricta posible.
  - /docs y /redoc: Swagger y ReDoc cargan sus assets de un CDN; con la politica
    estricta dejarian de renderizar, asi que se les permite ese origen.

HSTS solo se envia en produccion: en desarrollo se sirve por HTTP plano y la
cabecera obligaria al navegador a usar https, dejando el entorno inaccesible.
"""
import os

from starlette.middleware.base import BaseHTTPMiddleware

RUTAS_DOCS = ("/docs", "/redoc", "/openapi.json")

CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "frame-ancestors 'none'"
)

HSTS = "max-age=31536000; includeSubDomains"


def _en_produccion() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        respuesta = await call_next(request)

        es_docs = request.url.path.startswith(RUTAS_DOCS)
        respuesta.headers.setdefault(
            "Content-Security-Policy", CSP_DOCS if es_docs else CSP_API
        )
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        respuesta.headers.setdefault("Referrer-Policy", "no-referrer")

        if _en_produccion():
            respuesta.headers.setdefault("Strict-Transport-Security", HSTS)

        return respuesta
