"""
Dependencias de autenticación reutilizables en cualquier endpoint.

- get_current_user: lee el token Bearer, lo valida y devuelve el usuario.
- require_roles(...): fábrica de dependencias que exige uno o varios roles.

Uso en un endpoint:

    @router.get("/solo-admin")
    def algo(usuario = Depends(require_roles("superadmin"))):
        ...
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.security import decode_access_token

# Indica a FastAPI de dónde sale el token (habilita el botón "Authorize" en /docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas o token expirado",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Devuelve el usuario autenticado a partir del token, o lanza 401."""
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise _CREDENCIALES_INVALIDAS

    usuario = db.get(models.Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise _CREDENCIALES_INVALIDAS
    return usuario


def require_roles(*roles_permitidos: str):
    """Crea una dependencia que solo deja pasar a los roles indicados."""

    def verificar(usuario: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if usuario.rol.nombre not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return usuario

    return verificar
