"""Pruebas de los endpoints públicos (sin login) para la app."""


def _torneo(client, auth_admin, **extra):
    cuerpo = {"nombre": "Liga Apertura", "sede_id": 1, **extra}
    return client.post("/torneos", headers=auth_admin, json=cuerpo).json()


def test_inicio_sin_token(client):
    r = client.get("/publico/inicio")
    assert r.status_code == 200
    assert set(["proximos_partidos", "torneos_activos", "goleadores_top"]).issubset(r.json().keys())


def test_lista_torneos_activos_y_proximos(client, auth_admin):
    _torneo(client, auth_admin, nombre="En Curso", estado="en_curso")
    _torneo(client, auth_admin, nombre="Por Empezar", estado="programado",
            tipo="liga", cuota_inscripcion=500, premio="Trofeo + 10000",
            fecha_cierre_inscripciones="2026-07-01")

    r = client.get("/publico/torneos")  # sin token
    assert r.status_code == 200
    datos = r.json()
    assert any(t["nombre"] == "En Curso" for t in datos["activos"])
    assert any(t["nombre"] == "Por Empezar" for t in datos["proximos"])


def test_detalle_torneo_con_campos_de_inscripcion(client, auth_admin):
    tid = _torneo(client, auth_admin, nombre="Copa", estado="programado",
                  tipo="eliminacion", cuota_inscripcion=300.0, premio="Medallas",
                  fecha_cierre_inscripciones="2026-08-01")["id"]
    r = client.get(f"/publico/torneos/{tid}")
    assert r.status_code == 200
    d = r.json()
    assert d["tipo"] == "eliminacion" and d["cuota_inscripcion"] == 300.0
    assert d["premio"] == "Medallas" and d["fecha_cierre_inscripciones"] == "2026-08-01"
    assert d["sede_nombre"] == "Sede Central"


def test_tabla_y_goleadores_publicos(client, auth_admin):
    tid = _torneo(client, auth_admin, estado="en_curso")["id"]
    # sin partidos: tabla vacía, goleadores vacío, pero responden 200 sin token
    assert client.get(f"/publico/torneos/{tid}/tabla").status_code == 200
    assert client.get(f"/publico/torneos/{tid}/goleadores").status_code == 200
    assert client.get(f"/publico/torneos/{tid}/partidos").status_code == 200


def test_torneo_inexistente(client):
    assert client.get("/publico/torneos/999").status_code == 404


def test_publico_inicio_trae_ultimos_resultados(client, db_session):
    """/publico/inicio expone los últimos partidos finalizados (para el ticker
    del login del panel): más recientes primero, máximo 5, sin token."""
    from datetime import datetime, timedelta, timezone
    from app import models

    db = db_session()
    torneo = models.Torneo(nombre="Público Ticker", sede_id=1)
    db.add(torneo)
    db.commit()
    base = datetime(2026, 7, 1, 16, 0, tzinfo=timezone.utc)
    for i in range(6):
        db.add(models.Partido(
            torneo_id=torneo.id, equipo_local_id=1, equipo_visitante_id=2,
            estado="finalizado", goles_local=i, goles_visitante=1,
            fecha_hora=base + timedelta(days=i)))
    db.commit()
    db.close()

    r = client.get("/publico/inicio")
    assert r.status_code == 200
    resultados = r.json()["ultimos_resultados"]
    assert len(resultados) == 5                     # tope de 5
    fechas = [x["fecha_hora"] for x in resultados]
    assert fechas == sorted(fechas, reverse=True)   # más recientes primero
    assert all(x["estado"] == "finalizado" for x in resultados)
    assert {"equipo_local_nombre", "goles_local", "torneo_nombre"} <= set(resultados[0])
