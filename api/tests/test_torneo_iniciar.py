"""Iniciar torneo: columna jornada, generación de calendario y rondas."""


def test_partido_expone_jornada(client, db_session, auth_admin):
    from app import models
    db = db_session()
    torneo = models.Torneo(nombre="T Jornada", sede_id=1, tipo="liga")
    db.add(torneo)
    db.commit()
    p = models.Partido(torneo_id=torneo.id, equipo_local_id=1,
                       equipo_visitante_id=2, estado="programado", jornada=3)
    db.add(p)
    db.commit()
    pid = p.id
    db.close()

    r = client.get(f"/partidos/{pid}", headers=auth_admin)
    assert r.status_code == 200 and r.json()["jornada"] == 3
