"""
Utilidades de seguridad: hashing de contrasenas (bcrypt) y JWT.

- Las contrasenas NUNCA se guardan en texto plano; se almacena su hash.
- El token JWT lleva dentro el id del usuario y su rol, firmado con SECRET_KEY.
"""
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuracion leida del .env
SECRET_KEY = os.getenv("SECRET_KEY", "clave_insegura_solo_para_desarrollo")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

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
