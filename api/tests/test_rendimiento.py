"""
Regresión de N+1.

Los esquemas *Out exponen propiedades `*_nombre` que leen una relación. Sin
carga anticipada, un listado dispara una consulta extra por fila y por
relación. Estas pruebas cuentan los SELECT reales: si alguien quita el
`.options(*models.CARGA_*)` de un listado, el conteo crece con las filas y
falla aquí.

Detalle importante: cada fila apunta a entidades relacionadas DISTINTAS. Si
todas compartieran el mismo torneo/cancha/equipo, el mapa de identidad de
SQLAlchemy resolvería los lazy loads desde memoria tras la primera fila y el
N+1 quedaría invisible — la prueba pasaría incluso sin el arreglo.
"""
import contextlib
from datetime import date, time

from sqlalchemy import event

from app import models


@contextlib.contextmanager
def contar_selects(db_session):
    """Cuenta los SELECT emitidos contra el engine de pruebas."""
    engine = db_session.kw["bind"]
    consultas = []

    def registrar(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(engine, "before_cursor_execute", registrar)
    try:
        yield consultas
    finally:
        event.remove(engine, "before_cursor_execute", registrar)


def _sembrar_partidos(db, cuantos, arranque):
    """Crea `cuantos` partidos, cada uno con torneo, cancha, árbitro y equipos propios."""
    rol_arbitro = db.query(models.Rol).filter_by(nombre="arbitro").one()
    rol_entrenador = db.query(models.Rol).filter_by(nombre="entrenador").one()
    for i in range(arranque, arranque + cuantos):
        sede = models.Sede(nombre=f"Sede {i}", ciudad="Pachuca")
        db.add(sede)
        db.flush()
        cancha = models.Cancha(sede_id=sede.id, nombre=f"Cancha {i}", tipo="futbol 7",
                               precio_hora=200, disponible=True)
        torneo = models.Torneo(nombre=f"Torneo {i}", sede_id=sede.id, estado="en_curso")
        arbitro = models.Usuario(rol_id=rol_arbitro.id, nombre=f"Arbitro {i}",
                                 correo=f"arb{i}@demo.com", password_hash="x")
        entrenador = models.Usuario(rol_id=rol_entrenador.id, nombre=f"Entrenador {i}",
                                    correo=f"ent{i}@demo.com", password_hash="x")
        db.add_all([cancha, torneo, arbitro, entrenador])
        db.flush()
        local = models.Equipo(entrenador_id=entrenador.id, nombre=f"Local {i}")
        visitante = models.Equipo(entrenador_id=entrenador.id, nombre=f"Visitante {i}")
        db.add_all([local, visitante])
        db.flush()
        db.add(models.Partido(
            torneo_id=torneo.id, cancha_id=cancha.id, arbitro_id=arbitro.id,
            equipo_local_id=local.id, equipo_visitante_id=visitante.id,
            estado="programado",
        ))
    db.commit()


def test_listar_partidos_no_escala_con_las_filas(client, db_session, auth_admin):
    """PartidoOut lee cinco relaciones; listar no debe costar más por tener más filas."""
    db = db_session()
    _sembrar_partidos(db, 2, arranque=100)
    db.close()

    with contar_selects(db_session) as pocas:
        r = client.get("/partidos", headers=auth_admin)
    assert r.status_code == 200 and len(r.json()) == 2
    con_2 = len(pocas)

    db = db_session()
    _sembrar_partidos(db, 4, arranque=200)
    db.close()

    with contar_selects(db_session) as muchas:
        r = client.get("/partidos", headers=auth_admin)
    assert r.status_code == 200 and len(r.json()) == 6
    con_6 = len(muchas)

    # Con lazy loading serían ~5 SELECT extra por fila: 6 filas costarían unos
    # 20 más que 2. Con joinedload el coste es el mismo.
    assert con_6 == con_2, (
        f"listar 6 partidos costó {con_6} SELECT y listar 2 costó {con_2}: "
        "el listado volvió a caer en N+1 (¿se quitó el .options(*models.CARGA_PARTIDO)?)"
    )


def _sembrar_reservas(db, cuantos, arranque):
    """Crea `cuantos` reservas, cada una de un usuario y una cancha propios."""
    rol_jugador = db.query(models.Rol).filter_by(nombre="jugador").one()
    for i in range(arranque, arranque + cuantos):
        sede = models.Sede(nombre=f"Sede R{i}", ciudad="Pachuca")
        db.add(sede)
        db.flush()
        cancha = models.Cancha(sede_id=sede.id, nombre=f"Cancha R{i}", tipo="futbol 7",
                               precio_hora=200, disponible=True)
        usuario = models.Usuario(rol_id=rol_jugador.id, nombre=f"Jugador R{i}",
                                 correo=f"res{i}@demo.com", password_hash="x")
        db.add_all([cancha, usuario])
        db.flush()
        db.add(models.Reserva(
            usuario_id=usuario.id, cancha_id=cancha.id, fecha=date(2030, 1, 1),
            hora_inicio=time(8, 0), hora_fin=time(9, 0), estado="pendiente",
        ))
    db.commit()


def test_listar_reservas_no_escala_con_las_filas(client, db_session, auth_admin):
    """ReservaOut lee usuario y cancha."""
    db = db_session()
    _sembrar_reservas(db, 2, arranque=100)
    db.close()

    with contar_selects(db_session) as pocas:
        r = client.get("/reservas", headers=auth_admin)
    assert r.status_code == 200 and len(r.json()) == 2
    con_2 = len(pocas)

    db = db_session()
    _sembrar_reservas(db, 4, arranque=200)
    db.close()

    with contar_selects(db_session) as muchas:
        r = client.get("/reservas", headers=auth_admin)
    assert r.status_code == 200 and len(r.json()) == 6
    con_6 = len(muchas)

    assert con_6 == con_2, (
        f"listar 6 reservas costó {con_6} SELECT y listar 2 costó {con_2}: "
        "el listado volvió a caer en N+1 (¿se quitó el .options(*models.CARGA_RESERVA)?)"
    )
