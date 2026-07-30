"""La regla de quién está en el campo (app/campo.py)."""
from app import campo


def _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id, torneo_id, je_ids):
    """Crea el partido, guarda el plan del equipo 1 (obligatoriamente ANTES de
    iniciar) y lo pone en juego. je_ids son jugador_equipo_id de titulares."""
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    resp = client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": je, "posicion": "DEF", "orden": i}
                      for i, je in enumerate(je_ids)]})
    assert resp.status_code == 200, f"PUT /plan failed: {resp.status_code} {resp.text}"
    resp = client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert resp.status_code == 200, f"POST /iniciar failed: {resp.status_code} {resp.text}"
    return pid


def _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    resp = client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert resp.status_code == 200, f"POST /iniciar failed: {resp.status_code} {resp.text}"
    return pid


def _estado(db_session, pid, equipo_id=1):
    db = db_session()
    try:
        return campo.estado_campo(db, pid, equipo_id)
    finally:
        db.close()


def test_sin_plan_la_plantilla_entera_esta_en_campo(client, db_session, auth_admin,
                                                    auth_arbitro, arbitro_id, torneo_id, miembro_id):
    pid = _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    estado = _estado(db_session, pid)
    assert estado["hay_plan"] is False
    assert miembro_id in estado["en_campo"]


def test_con_plan_solo_los_titulares(client, db_session, auth_admin, auth_arbitro,
                                     auth_entrenador, agregar_miembro, arbitro_id, torneo_id):
    titular = agregar_miembro(auth_entrenador, 1, "Titular Campo", "titcampo@demo.com")
    banca = agregar_miembro(auth_entrenador, 1, "Banca Campo", "bancacampo@demo.com")
    pid = _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                    torneo_id, [titular["je_id"]])
    estado = _estado(db_session, pid)
    assert estado["hay_plan"] is True
    assert titular["jugador_id"] in estado["en_campo"]
    assert banca["jugador_id"] not in estado["en_campo"]


def test_expulsado_sale_del_campo(client, db_session, auth_admin, auth_arbitro,
                                  arbitro_id, torneo_id, miembro_id):
    pid = _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_roja", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 30})
    estado = _estado(db_session, pid)
    assert miembro_id in estado["expulsados"]
    assert miembro_id not in estado["en_campo"]


def test_el_que_sale_de_cambio_deja_el_campo_y_el_que_entra_lo_ocupa(
        client, db_session, auth_admin, auth_arbitro, auth_entrenador,
        agregar_miembro, arbitro_id, torneo_id):
    sale = agregar_miembro(auth_entrenador, 1, "Sale Campo", "salecampo@demo.com")
    entra = agregar_miembro(auth_entrenador, 1, "Entra Campo", "entracampo@demo.com")
    pid = _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                    torneo_id, [sale["je_id"]])
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "cambio", "equipo_id": 1, "jugador_id": sale["jugador_id"],
        "jugador_secundario_id": entra["jugador_id"], "minuto": 60})
    estado = _estado(db_session, pid)
    assert sale["jugador_id"] in estado["salidos"]
    assert sale["jugador_id"] not in estado["en_campo"]
    assert entra["jugador_id"] in estado["en_campo"]


def test_amarillas_se_cuentan_por_jugador(client, db_session, auth_admin, auth_arbitro,
                                          arbitro_id, torneo_id, miembro_id):
    pid = _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id)
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": miembro_id, "minuto": 20})
    estado = _estado(db_session, pid)
    assert estado["amarillas"].get(miembro_id) == 1


def test_amarillas_scoped_a_plantilla(client, db_session, auth_admin, auth_arbitro,
                                       auth_entrenador, agregar_miembro, arbitro_id, torneo_id):
    """Las amarillas solo incluyen jugadores de la plantilla del equipo."""
    # Crear dos jugadores: uno que se usa en el plan y otro que no (banca)
    titular = agregar_miembro(auth_entrenador, 1, "Titular Amarilla", "titamarl@demo.com")
    banca = agregar_miembro(auth_entrenador, 1, "Banca Amarilla", "bancaamarl@demo.com")

    pid = _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id,
                    torneo_id, [titular["je_id"]])

    # Dar amarilla a ambos
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": titular["jugador_id"], "minuto": 10})
    client.post(f"/partidos/{pid}/eventos", headers=auth_arbitro, json={
        "tipo": "tarjeta_amarilla", "equipo_id": 1, "jugador_id": banca["jugador_id"], "minuto": 15})

    # Verificar que ambos aparecen (ambos son de la plantilla)
    estado = _estado(db_session, pid, equipo_id=1)
    assert titular["jugador_id"] in estado["amarillas"]
    assert banca["jugador_id"] in estado["amarillas"]


def test_plan_sin_titulares_con_cuenta_hay_plan_es_verdadero(client, db_session, auth_admin,
                                                              auth_arbitro, auth_entrenador,
                                                              arbitro_id, torneo_id):
    """Si el plan existe pero todos los titulares carecen de cuenta registrada,
    hay_plan=True pero en_campo está vacío para usuarios registrados."""
    # Crear jugador sin cuenta: insertar directamente en DB un JugadorEquipo con jugador_id=None
    from app import models

    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]

    db = db_session()
    try:
        # Crear un JugadorEquipo sin usuario registrado (jugador_id=None)
        je = models.JugadorEquipo(
            equipo_id=1,
            jugador_id=None,  # Sin cuenta registrada
            nombre="Jugador Sin Cuenta",
            dorsal=99,
            posicion="DEF"
        )
        db.add(je)
        db.flush()
        je_id = je.id

        # Crear alineación con solo este jugador sin cuenta
        plan = models.AlineacionPlan(
            partido_id=pid,
            equipo_id=1,
            formacion="4-4-2",
            jugadores=[{"jugador_equipo_id": je_id, "posicion": "DEF", "orden": 0, "jugador_id": None}]
        )
        db.add(plan)
        db.commit()
    finally:
        db.close()

    # Iniciar el partido
    resp = client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    assert resp.status_code == 200

    # Verificar: hay_plan=True porque el plan fue registrado, pero en_campo vacío
    # (ya que el único titular no tiene cuenta)
    estado = _estado(db_session, pid, equipo_id=1)
    assert estado["hay_plan"] is True, "El plan fue registrado, así que hay_plan debe ser True"
    assert len(estado["en_campo"]) == 0, "No hay usuarios registrados en el plan, así que en_campo está vacío"
