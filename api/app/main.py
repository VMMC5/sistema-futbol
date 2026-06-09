"""
Punto de entrada de la API (FastAPI).

Usa la configuracion central de base de datos (app/database.py) y los
modelos (app/models.py). La documentacion interactiva queda en /docs.
"""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app import models  # noqa: F401  -> registra los modelos en la metadata
from app.routers import (
    auth, torneos, reservas, partidos, estadisticas,
    sedes, canchas, usuarios, publico, solicitudes,
)

app = FastAPI(
    title="API - Sistema Integral de Canchas y Torneos de Futbol",
    version="0.1.0",
)

# Routers por modulo
app.include_router(publico.router, prefix="/publico", tags=["publico"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(solicitudes.router, prefix="/solicitudes", tags=["solicitudes"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
app.include_router(sedes.router, prefix="/sedes", tags=["sedes"])
app.include_router(canchas.router, prefix="/canchas", tags=["canchas"])
app.include_router(torneos.router, prefix="/torneos", tags=["torneos"])
app.include_router(reservas.router, prefix="/reservas", tags=["reservas"])
app.include_router(partidos.router, prefix="/partidos", tags=["partidos"])
app.include_router(estadisticas.router, prefix="/estadisticas", tags=["estadisticas"])


@app.get("/")
def raiz():
    return {"mensaje": "API del sistema de torneos funcionando"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Comprueba que la API puede hablar con la base de datos."""
    try:
        db.execute(text("SELECT 1"))
        return {"api": "ok", "base_de_datos": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"api": "ok", "base_de_datos": "error", "detalle": str(e)}
