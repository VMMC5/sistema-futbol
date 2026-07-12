"""
URL de conexión que usan las migraciones.

Alembic necesita DDL para crear y alterar tablas, así que corre con un usuario
admin distinto del que usa la API en runtime (limitado a SELECT/INSERT/UPDATE/
DELETE). En desarrollo ese usuario admin no existe, y se reserva a las
credenciales de siempre.
"""
import os


def url_de_migraciones() -> str:
    usuario = os.getenv("DB_ADMIN_USER") or os.getenv("DB_USER")
    password = os.getenv("DB_ADMIN_PASSWORD") or os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "db")
    puerto = os.getenv("DB_PORT", "5432")
    nombre = os.getenv("DB_NAME")
    return f"postgresql+psycopg2://{usuario}:{password}@{host}:{puerto}/{nombre}"
