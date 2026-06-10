"""Pruebas del panel del entrenador: equipos, plantilla por invitación y stats."""


def _mis_equipos(client, auth):
    return client.get("/equipos", headers=auth).json()


def test_entrenador_ve_solo_sus_equipos(client, auth_entrenador, auth_admin):
    mios = _mis_equipos(client, auth_entrenador)
    assert len(mios) == 2  # Equipo A y B (seed)
    assert len(_mis_equipos(client, auth_admin)) >= 2


def test_crear_equipo_vacio(client, auth_entrenador):
    r = client.post("/equipos", headers=auth_entrenador, json={
        "nombre": "Halcones FC", "color": "Rojo", "categoria": "Liga A"})
    assert r.status_code == 201
    assert r.json()["jugadores_count"] == 0 and r.json()["categoria"] == "Liga A"


def test_buscar_jugadores_disponibles(client, auth_entrenador):
    # Dos jugadores registrados sin equipo
    for n, c in [("Ana López", "ana@demo.com"), ("Beto Ruiz", "beto@demo.com")]:
        client.post("/auth/register", json={"nombre": n, "correo": c, "password": "clave12345"})

    r = client.get("/equipos/jugadores-disponibles", headers=auth_entrenador)
    assert r.status_code == 200
    nombres = {j["nombre"] for j in r.json()}
    assert {"Ana López", "Beto Ruiz"}.issubset(nombres)
    # 'Miembro' ya está en el Equipo A => NO debe aparecer
    assert "Miembro" not in nombres
    # Búsqueda por nombre
    r2 = client.get("/equipos/jugadores-disponibles?buscar=ana", headers=auth_entrenador)
    assert all("ana" in j["nombre"].lower() for j in r2.json())


def test_invitar_y_aceptar(client, auth_entrenador, agregar_miembro):
    info = agregar_miembro(auth_entrenador, 1, "Nuevo Jugador", "nuevo@demo.com")
    eq = client.get("/equipos/1", headers=auth_entrenador).json()
    assert any(j["jugador_id"] == info["jugador_id"] for j in eq["jugadores"])
    # Ya en un equipo => no aparece en disponibles
    disp = client.get("/equipos/jugadores-disponibles", headers=auth_entrenador).json()
    assert all(j["id"] != info["jugador_id"] for j in disp)


def test_no_invitar_si_ya_tiene_equipo(client, auth_entrenador, miembro_id):
    # 'miembro' ya pertenece al Equipo A
    r = client.post("/equipos/1/invitaciones", headers=auth_entrenador, json={"jugador_id": miembro_id})
    assert r.status_code == 409


def test_editar_y_quitar_jugador(client, auth_entrenador, agregar_miembro):
    info = agregar_miembro(auth_entrenador, 1, "Editable", "editable@demo.com")
    # Editar dorsal/posición
    r = client.put(f"/equipos/1/jugadores/{info['je_id']}", headers=auth_entrenador,
                   json={"dorsal": 7, "posicion": "Medio"})
    assert r.status_code == 200
    je = next(j for j in r.json()["jugadores"] if j["id"] == info["je_id"])
    assert je["dorsal"] == 7 and je["posicion"] == "Medio"
    # Quitar
    r = client.delete(f"/equipos/1/jugadores/{info['je_id']}", headers=auth_entrenador)
    assert r.status_code == 200
    assert all(j["id"] != info["je_id"] for j in r.json()["jugadores"])


def test_no_puede_ver_equipo_ajeno(client, auth_entrenador, auth_admin):
    ajeno = client.post("/equipos", headers=auth_admin, json={"nombre": "Del Admin"}).json()["id"]
    assert client.get(f"/equipos/{ajeno}", headers=auth_entrenador).status_code == 403


def test_resumen_entrenador(client, auth_entrenador):
    r = client.get("/equipos/resumen", headers=auth_entrenador)
    assert r.status_code == 200
    assert r.json()["equipos_count"] == 2 and r.json()["equipo_principal"] is not None


def test_estadisticas_equipo(client, auth_entrenador):
    eid = _mis_equipos(client, auth_entrenador)[0]["id"]
    r = client.get(f"/equipos/{eid}/estadisticas", headers=auth_entrenador)
    assert r.status_code == 200
    for k in ["pj", "pg", "pe", "pp", "posicion", "goleadores"]:
        assert k in r.json()


def test_borrar_equipo_sin_dependencias(client, auth_entrenador):
    eid = client.post("/equipos", headers=auth_entrenador, json={"nombre": "Borrable"}).json()["id"]
    assert client.delete(f"/equipos/{eid}", headers=auth_entrenador).status_code == 204
