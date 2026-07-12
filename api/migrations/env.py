"""
Entorno de Alembic.

- La URL de conexión se toma de las MISMAS variables de entorno que usa la app
  (definidas en el .env), así no se duplican credenciales en alembic.ini.
- target_metadata apunta a la Base de los modelos, lo que permite
  `alembic revision --autogenerate` para detectar cambios en las tablas.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic carga este archivo directamente (no como parte del paquete), así que
# el propio directorio migrations/ no queda en sys.path por defecto: hay que
# añadirlo a mano para poder importar url_bd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar la metadata de los modelos
from app.database import Base
from app import models  # noqa: F401  -> asegura que todos los modelos se registren
from url_bd import url_de_migraciones

config = context.config

# Construir la URL desde el entorno (igual que app/database.py), con un
# usuario admin separado del limitado que usa la API en runtime.
DATABASE_URL = url_de_migraciones()
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse a la base de datos."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones conectándose a la base de datos."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
