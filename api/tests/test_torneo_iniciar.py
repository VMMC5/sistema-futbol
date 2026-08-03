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


# ---------- helpers ----------
def _torneo(client, auth_admin, tipo="Liga", **over):
    body = {"nombre": f"Torneo {tipo}", "sede_id": 1, "tipo": tipo}
    body.update(over)
    return client.post("/torneos", headers=auth_admin, json=body).json()["id"]


def _inscribir_aceptados(db_session, torneo_id, equipo_ids):
    from app import models
    db = db_session()
    for eid in equipo_ids:
        db.add(models.Inscripcion(torneo_id=torneo_id, equipo_id=eid, estado="aceptada"))
    db.commit()
    db.close()


def _equipos_extra(db_session, n):
    """Crea n equipos más (el seed trae 2, del mismo entrenador)."""
    from app import models
    db = db_session()
    base = db.query(models.Equipo).first()
    nuevos = [models.Equipo(entrenador_id=base.entrenador_id, nombre=f"Extra {i}")
              for i in range(n)]
    db.add_all(nuevos)
    db.commit()
    ids = [e.id for e in nuevos]
    db.close()
    return ids


# ---------- iniciar: liga ----------
def test_iniciar_liga_dos_equipos(client, db_session, auth_admin):
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])

    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 200, r.text
    assert r.json()["partidos_creados"] == 2      # ida y vuelta
    assert r.json()["estado"] == "en_curso"

    partidos = client.get(f"/partidos?torneo_id={tid}", headers=auth_admin).json()
    assert sorted(p["jornada"] for p in partidos) == [1, 2]
    ida, vuelta = sorted(partidos, key=lambda p: p["jornada"])
    # localía invertida entre ida y vuelta
    assert (ida["equipo_local_id"], ida["equipo_visitante_id"]) == \
           (vuelta["equipo_visitante_id"], vuelta["equipo_local_id"])
    # jornadas separadas una semana
    assert ida["fecha_hora"][:10] == "2026-09-05"
    assert vuelta["fecha_hora"][:10] == "2026-09-12"


def test_iniciar_valida_estado_tipo_e_inscripciones(client, db_session, auth_admin):
    # tipo no reconocido
    tid = _torneo(client, auth_admin, tipo="Copa rara")
    _inscribir_aceptados(db_session, tid, [1, 2])
    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 400

    # menos de 2 aceptadas
    tid2 = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid2, [1])
    r = client.post(f"/torneos/{tid2}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 400

    # ya en curso -> 409
    tid3 = _torneo(client, auth_admin, tipo="Liga", estado="en_curso")
    r = client.post(f"/torneos/{tid3}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 409


def test_iniciar_eliminacion_seis_equipos(client, db_session, auth_admin):
    extras = _equipos_extra(db_session, 4)
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    _inscribir_aceptados(db_session, tid, [1, 2] + extras)

    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "10:00"})
    assert r.status_code == 200, r.text
    # 6 equipos -> 2 byes y 2 partidos de ronda 1 (regla de potencia de 2)
    assert r.json()["partidos_creados"] == 2
    partidos = client.get(f"/partidos?torneo_id={tid}", headers=auth_admin).json()
    assert all(p["jornada"] == 1 for p in partidos)
    # escalonados +2h el mismo día
    horas = sorted(p["fecha_hora"][11:16] for p in partidos)
    assert horas == ["10:00", "12:00"]


def test_iniciar_notifica_una_vez_por_entrenador(client, db_session, auth_admin):
    from app import models
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])   # mismo entrenador (seed)
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    db = db_session()
    avisos = (db.query(models.Notificacion)
              .filter(models.Notificacion.titulo == "Torneo iniciado").count())
    db.close()
    assert avisos == 1   # dos equipos, un entrenador -> UNA notificación


# ---------- siguiente-ronda ----------
def _finalizar_ronda(db_session, torneo_id, ronda):
    """Marca finalizados los partidos de la ronda con marcadores SIN empate."""
    from app import models
    db = db_session()
    partidos = (db.query(models.Partido)
                .filter_by(torneo_id=torneo_id, jornada=ronda).all())
    for i, p in enumerate(partidos):
        p.goles_local, p.goles_visitante = (2, 1) if i % 2 == 0 else (0, 3)
        p.estado = "finalizado"
    db.commit()
    db.close()
    return len(partidos)


def test_siguiente_ronda_flujo_completo_seis_equipos(client, db_session, auth_admin):
    extras = _equipos_extra(db_session, 4)
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    _inscribir_aceptados(db_session, tid, [1, 2] + extras)
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "10:00"})

    # ronda 1 incompleta -> 409
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "10:00"})
    assert r.status_code == 409

    # ronda 2 = 2 ganadores + 2 byes = 4 equipos -> 2 partidos
    _finalizar_ronda(db_session, tid, 1)
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "10:00"})
    assert r.status_code == 200, r.text
    assert r.json() == {"ronda": 2, "partidos_creados": 2, "estado": "en_curso"}

    # ronda 3: la final
    _finalizar_ronda(db_session, tid, 2)
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-19", "hora_base": "10:00"})
    assert r.status_code == 200 and r.json()["partidos_creados"] == 1

    # campeón: el torneo finaliza
    _finalizar_ronda(db_session, tid, 3)
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-26", "hora_base": "10:00"})
    assert r.status_code == 200
    assert r.json()["estado"] == "finalizado" and r.json()["partidos_creados"] == 0
    assert "campeon" in r.json()
    torneo = client.get(f"/torneos/{tid}", headers=auth_admin).json()
    assert torneo["estado"] == "finalizado"


def test_siguiente_ronda_rechaza_liga(client, db_session, auth_admin):
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "16:00"})
    assert r.status_code == 400


def test_siguiente_ronda_rechaza_empate_sin_cerrar(client, db_session, auth_admin):
    """Un partido finalizado y empatado en la ronda no debería poder existir
    (lo bloquea /finalizar), pero puede colarse por datos legacy, por borrar el
    evento de gol que desempataba, o por cambiar el tipo del torneo a mitad de
    camino. Sin este guardia, siguiente-ronda coronaría al visitante en silencio."""
    from app import models
    tid = _torneo(client, auth_admin, tipo="Eliminación directa")
    _inscribir_aceptados(db_session, tid, [1, 2])
    client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                json={"primera_fecha": "2026-09-05", "hora_base": "10:00"})

    db = db_session()
    p = (db.query(models.Partido).filter_by(torneo_id=tid, jornada=1).first())
    p.goles_local, p.goles_visitante = (1, 1)
    p.estado = "finalizado"
    db.commit()
    db.close()

    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "10:00"})
    assert r.status_code == 409
    assert "empatad" in r.json()["detail"].lower()


def test_siguiente_ronda_sin_calendario_no_500(client, db_session, auth_admin):
    """Un torneo de eliminación puesto 'en_curso' a mano (sin pasar por
    /iniciar) no tiene partidos: max() sobre una lista vacía explotaría con
    ValueError si no se le da un default."""
    from app import models
    db = db_session()
    torneo = models.Torneo(nombre="Sin calendario", sede_id=1,
                           tipo="eliminacion directa", estado="en_curso")
    db.add(torneo)
    db.commit()
    tid = torneo.id
    db.close()

    r = client.post(f"/torneos/{tid}/siguiente-ronda", headers=auth_admin,
                    json={"fecha": "2026-09-12", "hora_base": "10:00"})
    assert r.status_code == 409
    assert "calendario" in r.json()["detail"].lower()


def test_iniciar_no_es_idempotente(client, db_session, auth_admin):
    """El estado puede volver a 'programado' vía PUT /torneos/{id}: iniciar
    de nuevo no debe duplicar el calendario ya generado."""
    tid = _torneo(client, auth_admin, tipo="Liga")
    _inscribir_aceptados(db_session, tid, [1, 2])
    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-05", "hora_base": "16:00"})
    assert r.status_code == 200, r.text

    r = client.put(f"/torneos/{tid}", headers=auth_admin, json={"estado": "programado"})
    assert r.status_code == 200, r.text

    r = client.post(f"/torneos/{tid}/iniciar", headers=auth_admin,
                    json={"primera_fecha": "2026-09-12", "hora_base": "16:00"})
    assert r.status_code == 409
    assert "calendario" in r.json()["detail"].lower()
