"""
Punto de entrada de la API (FastAPI).

Esto es un esqueleto mínimo y funcional: arranca, responde un saludo,
expone un /health que comprueba la conexión con PostgreSQL, y deja
listo el lugar donde irán sus routers (jugadores, torneos, partidos, etc.).

La documentación interactiva queda en  http://localhost:8000/docs
"""
import os

from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI(
    title="API - Sistema Integral de Canchas y Torneos de Fútbol",
    version="0.1.0",
)

# Cadena de conexión construida desde las variables de entorno (.env).
# OJO: el host es "db", que es el nombre del servicio en docker-compose.
DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'db')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@app.get("/")
def raiz():
    return {"mensaje": "API del sistema de torneos funcionando 🟢"}


@app.get("/health")
def health():
    """Comprueba que la API puede hablar con la base de datos."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"api": "ok", "base_de_datos": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"api": "ok", "base_de_datos": "error", "detalle": str(e)}


# A partir de aquí irán sus routers, por ejemplo:
# from app.routers import jugadores, torneos, partidos
# app.include_router(jugadores.router, prefix="/jugadores", tags=["jugadores"])
