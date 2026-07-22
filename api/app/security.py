"""
Utilidades de seguridad: hashing de contrasenas (bcrypt) y JWT.

- Las contrasenas NUNCA se guardan en texto plano; se almacena su hash.
- El token JWT lleva dentro el id del usuario y su rol, firmado con SECRET_KEY.
"""
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuracion leida del .env.
# SECRET_KEY es obligatoria: sin ella los JWT serian falsificables, asi que la
# app se niega a arrancar en lugar de caer a una clave por defecto insegura.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no esta definida. Configurala en el entorno (.env) con una "
        "llave larga y aleatoria, por ejemplo: openssl rand -hex 32"
    )
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# 12 horas. No hay refresh token todavia: cuando el access token expira, la app
# movil expulsa al usuario al login en medio de lo que este haciendo. Una jornada
# de trabajo cabe en este margen. Al implementar el refresh token, este valor
# debe volver a bajar (60 min o menos), que es lo correcto para un token de acceso.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena."""
    return pwd_context.hash(password)


def verify_password(plano: str, hashed: str) -> bool:
    """Compara una contrasena en texto plano contra su hash."""
    return pwd_context.verify(plano, hashed)


def create_access_token(*, usuario_id: int, rol: str) -> str:
    """Crea un JWT firmado que identifica al usuario y su rol."""
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": expira,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    """Verifica y decodifica un JWT. Devuelve el payload o None si es invalido."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
