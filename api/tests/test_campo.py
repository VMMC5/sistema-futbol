"""La regla de quién está en el campo (app/campo.py)."""
from app import campo


def _con_plan(client, auth_admin, auth_arbitro, auth_entrenador, arbitro_id, torneo_id, je_ids):
    """Crea el partido, guarda el plan del equipo 1 (obligatoriamente ANTES de
    iniciar) y lo pone en juego. je_ids son jugador_equipo_id de titulares."""
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.put(f"/partidos/{pid}/plan", headers=auth_entrenador, json={
        "equipo_id": 1, "formacion": "4-4-2",
        "jugadores": [{"jugador_equipo_id": je, "posicion": "DEF", "orden": i}
                      for i, je in enumerate(je_ids)]})
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
    return pid


def _sin_plan(client, auth_admin, auth_arbitro, arbitro_id, torneo_id):
    pid = client.post("/partidos", headers=auth_admin, json={
        "torneo_id": torneo_id, "equipo_local_id": 1, "equipo_visitante_id": 2,
        "arbitro_id": arbitro_id,
    }).json()["id"]
    client.post(f"/partidos/{pid}/iniciar", headers=auth_arbitro)
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
