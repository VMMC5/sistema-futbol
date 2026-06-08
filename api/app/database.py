"""
Configuración central de la base de datos (SQLAlchemy).

Aquí vive la conexión a PostgreSQL, la fábrica de sesiones y la clase Base
de la que heredan todos los modelos. Los endpoints obtienen una sesión
mediante la dependencia `get_db`.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Construida desde las variables del .env. El host "db" es el nombre del
# servicio en docker-compose.
DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'db')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Todas las tablas heredan de esta Base.
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
