"""
Configuración de pruebas (pytest).

Usa una base de datos SQLite EN MEMORIA (no toca PostgreSQL), con un
StaticPool para que todas las sesiones compartan la misma base. Cada prueba
arranca con las tablas creadas y unos datos mínimos sembrados.
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Variables mínimas para que los módulos importen sin un .env real
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "secret_de_pruebas")
os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads_test")
os.environ.setdefault("UPLOAD_DIR", "/tmp/test_uploads_torneos")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app import models  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    db = TestingSession()
    # Datos base: roles, una sede y un superadmin
    roles = {n: models.Rol(nombre=n) for n in ["jugador", "entrenador", "arbitro", "superadmin"]}
    db.add_all(roles.values())
    db.flush()
    db.add(models.Sede(nombre="Sede Central", ciudad="Pachuca"))
    db.flush()
    db.add(models.Cancha(sede_id=1, nombre="Cancha 1", tipo="futbol 7",
                         precio_hora=200, disponible=True))
    db.add(models.Usuario(
        rol_id=roles["superadmin"].id, nombre="Admin",
        correo="admin@demo.com", password_hash=hash_password("adminpass123"),
    ))
    # Para las pruebas de partidos: un arbitro, un entrenador, dos equipos y un torneo
    arbitro = models.Usuario(
        rol_id=roles["arbitro"].id, nombre="Arbitro",
        correo="arbitro@demo.com", password_hash=hash_password("arbitropass123"),
    )
    entrenador = models.Usuario(
        rol_id=roles["entrenador"].id, nombre="Entrenador",
        correo="entrenador@demo.com", password_hash=hash_password("entrenadorpass123"),
    )
    miembro = models.Usuario(
        rol_id=roles["jugador"].id, nombre="Miembro",
        correo="miembro@demo.com", password_hash=hash_password("miembropass123"),
    )
    db.add_all([arbitro, entrenador, miembro])
    db.flush()
    equipos = [
        models.Equipo(entrenador_id=entrenador.id, nombre="Equipo A"),
        models.Equipo(entrenador_id=entrenador.id, nombre="Equipo B"),
    ]
    db.add_all(equipos)
    db.flush()
    # 'miembro' pertenece al Equipo A (id=1) -> puede ser alineado
    db.add(models.JugadorEquipo(equipo_id=equipos[0].id, jugador_id=miembro.id, dorsal=10, posicion="delantero"))
    db.commit()

    yield TestingSession

    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    def override_db():
        d = db_session()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def token_admin(client):
    r = client.post("/auth/login", json={"correo": "admin@demo.com", "password": "adminpass123"})
    return r.json()["access_token"]


@pytest.fixture
def auth_admin(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def auth_arbitro(client):
    r = client.post("/auth/login", json={"correo": "arbitro@demo.com", "password": "arbitropass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def arbitro_id(client, auth_arbitro):
    return client.get("/auth/me", headers=auth_arbitro).json()["id"]


@pytest.fixture
def torneo_id(client, auth_admin):
    """Crea un torneo (vía API) y devuelve su id. Para las pruebas de partidos."""
    r = client.post("/torneos", headers=auth_admin, json={"nombre": "Liga de Prueba", "sede_id": 1})
    return r.json()["id"]


@pytest.fixture
def auth_entrenador(client):
    r = client.post("/auth/login", json={"correo": "entrenador@demo.com", "password": "entrenadorpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def miembro_id(client):
    """Id del jugador que pertenece al Equipo A (id=1)."""
    r = client.post("/auth/login", json={"correo": "miembro@demo.com", "password": "miembropass123"})
    tok = r.json()["access_token"]
    return client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]


@pytest.fixture
def agregar_miembro(client):
    """Incorpora un jugador a un equipo vía el flujo de invitación (registrar,
    invitar, aceptar) y devuelve sus ids/credenciales."""
    def _add(auth_entrenador, equipo_id, nombre, correo, password="clave12345"):
        client.post("/auth/register", json={"nombre": nombre, "correo": correo, "password": password})
        tok = client.post("/auth/login", json={"correo": correo, "password": password}).json()["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}
        jid = client.get("/auth/me", headers=headers).json()["id"]
        inv = client.post(f"/equipos/{equipo_id}/invitaciones", headers=auth_entrenador, json={"jugador_id": jid}).json()
        client.post(f"/invitaciones/{inv['id']}/aceptar", headers=headers)
        eq = client.get(f"/equipos/{equipo_id}", headers=auth_entrenador).json()
        je = next(j for j in eq["jugadores"] if j["jugador_id"] == jid)
        return {"jugador_id": jid, "je_id": je["id"], "token": tok, "headers": headers}
    return _add
