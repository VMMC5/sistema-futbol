"""
Panel de administración (Flask) — consume la API.

Patrón: el usuario inicia sesión contra la API, que devuelve un JWT; el token
se guarda en la sesión de Flask y se reenvía como Bearer en cada llamada a la
API. El panel está pensado para el rol 'superadmin'.
"""
import os
from functools import wraps

import requests
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")

API_URL = os.getenv("API_URL", "http://api:8000")
TIMEOUT = 5


# ----------------------------------------------------------------------
# Helpers para hablar con la API
# ----------------------------------------------------------------------
def _headers():
    return {"Authorization": f"Bearer {session.get('token', '')}"}


def api_get(path, **params):
    return requests.get(f"{API_URL}{path}", headers=_headers(), params=params, timeout=TIMEOUT)


def api_post(path, payload):
    return requests.post(f"{API_URL}{path}", headers=_headers(), json=payload, timeout=TIMEOUT)


def api_put(path, payload):
    return requests.put(f"{API_URL}{path}", headers=_headers(), json=payload, timeout=TIMEOUT)


def api_delete(path):
    return requests.delete(f"{API_URL}{path}", headers=_headers(), timeout=TIMEOUT)


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def _detalle_error(respuesta, por_defecto="Ocurrió un error"):
    try:
        return respuesta.json().get("detail", por_defecto)
    except Exception:  # noqa: BLE001
        return por_defecto


# ----------------------------------------------------------------------
# Autenticación
# ----------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
        password = request.form.get("password", "")
        try:
            r = requests.post(
                f"{API_URL}/auth/login",
                json={"correo": correo, "password": password},
                timeout=TIMEOUT,
            )
        except requests.RequestException:
            flash("No se pudo conectar con la API. ¿Está corriendo?", "error")
            return render_template("login.html")

        if r.status_code != 200:
            flash("Correo o contraseña incorrectos.", "error")
            return render_template("login.html")

        token = r.json()["access_token"]
        me = requests.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        ).json()

        # El panel es solo para administradores
        if me.get("rol") != "superadmin":
            flash("Este panel es solo para administradores.", "error")
            return render_template("login.html")

        session["token"] = token
        session["usuario"] = me
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("login"))


# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    # Estado de la API
    try:
        salud = requests.get(f"{API_URL}/health", timeout=TIMEOUT).json()
    except requests.RequestException:
        salud = {"api": "sin conexión", "base_de_datos": "?"}

    # Conteo de torneos
    r = api_get("/torneos")
    if r.status_code == 401:
        return _sesion_expirada()
    torneos = r.json() if r.status_code == 200 else []

    return render_template("dashboard.html", salud=salud, total_torneos=len(torneos))


# ----------------------------------------------------------------------
# Torneos
# ----------------------------------------------------------------------
@app.route("/torneos")
@login_required
def torneos():
    r = api_get("/torneos")
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template("torneos.html", torneos=r.json() if r.status_code == 200 else [])


@app.route("/torneos/nuevo", methods=["GET", "POST"])
@login_required
def torneo_nuevo():
    rs = api_get("/sedes")
    if rs.status_code == 401:
        return _sesion_expirada()
    sedes = rs.json() if rs.status_code == 200 else []

    if request.method == "POST":
        payload = {
            "nombre": request.form.get("nombre", "").strip(),
            "sede_id": int(request.form.get("sede_id", 1)),
            "descripcion": request.form.get("descripcion", "").strip() or None,
            "estado": request.form.get("estado", "programado"),
        }
        cupo = request.form.get("cupo_maximo", "").strip()
        if cupo:
            payload["cupo_maximo"] = int(cupo)

        r = api_post("/torneos", payload)
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 201:
            flash("Torneo creado correctamente.", "ok")
            return redirect(url_for("torneos"))
        flash(_detalle_error(r, "No se pudo crear el torneo."), "error")

    return render_template("torneo_nuevo.html", sedes=sedes)


@app.route("/torneos/<int:torneo_id>/tabla")
@login_required
def tabla(torneo_id):
    rt = api_get(f"/torneos/{torneo_id}")
    if rt.status_code == 401:
        return _sesion_expirada()
    torneo = rt.json() if rt.status_code == 200 else {"id": torneo_id, "nombre": f"Torneo {torneo_id}"}

    rtab = api_get(f"/estadisticas/torneos/{torneo_id}/tabla")
    filas = rtab.json() if rtab.status_code == 200 else []
    return render_template("tabla.html", torneo=torneo, filas=filas)


# ----------------------------------------------------------------------
# Sedes
# ----------------------------------------------------------------------
@app.route("/sedes")
@login_required
def sedes():
    r = api_get("/sedes")
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template("sedes.html", sedes=r.json() if r.status_code == 200 else [])


@app.route("/sedes/nueva", methods=["GET", "POST"])
@login_required
def sede_nueva():
    if request.method == "POST":
        r = api_post("/sedes", _form_sede())
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 201:
            flash("Sede creada correctamente.", "ok")
            return redirect(url_for("sedes"))
        flash(_detalle_error(r, "No se pudo crear la sede."), "error")
    return render_template("sede_form.html", sede=None, accion="Crear sede")


@app.route("/sedes/<int:sede_id>/editar", methods=["GET", "POST"])
@login_required
def sede_editar(sede_id):
    if request.method == "POST":
        r = api_put(f"/sedes/{sede_id}", _form_sede())
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 200:
            flash("Sede actualizada.", "ok")
            return redirect(url_for("sedes"))
        flash(_detalle_error(r, "No se pudo actualizar la sede."), "error")

    r = api_get(f"/sedes/{sede_id}")
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code != 200:
        flash("Sede no encontrada.", "error")
        return redirect(url_for("sedes"))
    return render_template("sede_form.html", sede=r.json(), accion="Guardar cambios")


@app.route("/sedes/<int:sede_id>/eliminar", methods=["POST"])
@login_required
def sede_eliminar(sede_id):
    r = api_delete(f"/sedes/{sede_id}")
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 204:
        flash("Sede eliminada.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo eliminar la sede."), "error")
    return redirect(url_for("sedes"))


def _form_sede():
    return {
        "nombre": request.form.get("nombre", "").strip(),
        "direccion": request.form.get("direccion", "").strip() or None,
        "ciudad": request.form.get("ciudad", "").strip() or None,
        "telefono": request.form.get("telefono", "").strip() or None,
    }


# ----------------------------------------------------------------------
# Canchas
# ----------------------------------------------------------------------
TIPOS_CANCHA = ["futbol 5", "futbol 7", "futbol 11"]


@app.route("/canchas")
@login_required
def canchas():
    r = api_get("/canchas")
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template("canchas.html", canchas=r.json() if r.status_code == 200 else [])


@app.route("/canchas/nueva", methods=["GET", "POST"])
@login_required
def cancha_nueva():
    sedes = _listar_sedes()
    if sedes is None:
        return _sesion_expirada()

    if request.method == "POST":
        r = api_post("/canchas", _form_cancha())
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 201:
            flash("Cancha creada correctamente.", "ok")
            return redirect(url_for("canchas"))
        flash(_detalle_error(r, "No se pudo crear la cancha."), "error")

    return render_template("cancha_form.html", cancha=None, sedes=sedes,
                           tipos=TIPOS_CANCHA, accion="Crear cancha")


@app.route("/canchas/<int:cancha_id>/editar", methods=["GET", "POST"])
@login_required
def cancha_editar(cancha_id):
    sedes = _listar_sedes()
    if sedes is None:
        return _sesion_expirada()

    if request.method == "POST":
        r = api_put(f"/canchas/{cancha_id}", _form_cancha())
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 200:
            flash("Cancha actualizada.", "ok")
            return redirect(url_for("canchas"))
        flash(_detalle_error(r, "No se pudo actualizar la cancha."), "error")

    r = api_get(f"/canchas/{cancha_id}")
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code != 200:
        flash("Cancha no encontrada.", "error")
        return redirect(url_for("canchas"))
    return render_template("cancha_form.html", cancha=r.json(), sedes=sedes,
                           tipos=TIPOS_CANCHA, accion="Guardar cambios")


@app.route("/canchas/<int:cancha_id>/eliminar", methods=["POST"])
@login_required
def cancha_eliminar(cancha_id):
    r = api_delete(f"/canchas/{cancha_id}")
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 204:
        flash("Cancha eliminada.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo eliminar la cancha."), "error")
    return redirect(url_for("canchas"))


def _listar_sedes():
    """Devuelve la lista de sedes, o None si la sesión expiró."""
    r = api_get("/sedes")
    if r.status_code == 401:
        return None
    return r.json() if r.status_code == 200 else []


def _form_cancha():
    payload = {
        "sede_id": int(request.form.get("sede_id", 1)),
        "nombre": request.form.get("nombre", "").strip(),
        "tipo": request.form.get("tipo") or None,
        "disponible": request.form.get("disponible") == "on",
    }
    precio = request.form.get("precio_hora", "").strip()
    payload["precio_hora"] = float(precio) if precio else None
    return payload


# ----------------------------------------------------------------------
# Usuarios
# ----------------------------------------------------------------------
@app.route("/usuarios")
@login_required
def usuarios():
    r = api_get("/usuarios")
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template("usuarios.html",
                           usuarios=r.json() if r.status_code == 200 else [],
                           yo_id=(session.get("usuario") or {}).get("id"))


@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
def usuario_nuevo():
    roles = _listar_roles()
    if roles is None:
        return _sesion_expirada()

    if request.method == "POST":
        payload = {
            "nombre": request.form.get("nombre", "").strip(),
            "correo": request.form.get("correo", "").strip(),
            "password": request.form.get("password", ""),
            "rol": request.form.get("rol", "jugador"),
            "telefono": request.form.get("telefono", "").strip() or None,
        }
        r = api_post("/usuarios", payload)
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 201:
            flash("Usuario creado correctamente.", "ok")
            return redirect(url_for("usuarios"))
        flash(_detalle_error(r, "No se pudo crear el usuario."), "error")

    return render_template("usuario_form.html", usuario=None, roles=roles, accion="Crear usuario")


@app.route("/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
def usuario_editar(usuario_id):
    roles = _listar_roles()
    if roles is None:
        return _sesion_expirada()

    if request.method == "POST":
        payload = {
            "nombre": request.form.get("nombre", "").strip(),
            "rol": request.form.get("rol"),
            "telefono": request.form.get("telefono", "").strip() or None,
            "activo": request.form.get("activo") == "on",
        }
        nueva = request.form.get("password", "").strip()
        if nueva:
            payload["password"] = nueva

        r = api_put(f"/usuarios/{usuario_id}", payload)
        if r.status_code == 401:
            return _sesion_expirada()
        if r.status_code == 200:
            flash("Usuario actualizado.", "ok")
            return redirect(url_for("usuarios"))
        flash(_detalle_error(r, "No se pudo actualizar el usuario."), "error")

    r = api_get(f"/usuarios/{usuario_id}")
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code != 200:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for("usuarios"))
    return render_template("usuario_form.html", usuario=r.json(), roles=roles, accion="Guardar cambios")


@app.route("/usuarios/<int:usuario_id>/estado", methods=["POST"])
@login_required
def usuario_estado(usuario_id):
    activar = request.form.get("activar") == "1"
    r = api_put(f"/usuarios/{usuario_id}", {"activo": activar})
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 200:
        flash("Usuario activado." if activar else "Usuario desactivado.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo cambiar el estado."), "error")
    return redirect(url_for("usuarios"))


def _listar_roles():
    """Devuelve la lista de roles, o None si la sesión expiró."""
    r = api_get("/usuarios/roles")
    if r.status_code == 401:
        return None
    return r.json() if r.status_code == 200 else ["jugador", "entrenador", "arbitro", "superadmin"]


# ----------------------------------------------------------------------
# Partidos (operativo)
# ----------------------------------------------------------------------
@app.route("/partidos")
@login_required
def partidos():
    r = api_get("/partidos")
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template("partidos.html", partidos=r.json() if r.status_code == 200 else [])


@app.route("/partidos/<int:partido_id>")
@login_required
def partido_detalle(partido_id):
    rp = api_get(f"/partidos/{partido_id}")
    if rp.status_code == 401:
        return _sesion_expirada()
    if rp.status_code != 200:
        flash("Partido no encontrado.", "error")
        return redirect(url_for("partidos"))

    eventos = api_get(f"/partidos/{partido_id}/eventos")
    alineacion = api_get(f"/partidos/{partido_id}/alineacion")
    return render_template(
        "partido_detalle.html",
        partido=rp.json(),
        eventos=eventos.json() if eventos.status_code == 200 else [],
        alineacion=alineacion.json() if alineacion.status_code == 200 else [],
    )


@app.route("/partidos/<int:partido_id>/<accion>", methods=["POST"])
@login_required
def partido_accion(partido_id, accion):
    if accion not in ("iniciar", "finalizar"):
        flash("Acción no válida.", "error")
        return redirect(url_for("partido_detalle", partido_id=partido_id))
    r = api_post(f"/partidos/{partido_id}/{accion}", {})
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 200:
        flash(f"Partido {'iniciado' if accion == 'iniciar' else 'finalizado'}.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo completar la acción."), "error")
    return redirect(url_for("partido_detalle", partido_id=partido_id))


# ----------------------------------------------------------------------
# Reservas (operativo)
# ----------------------------------------------------------------------
@app.route("/reservas")
@login_required
def reservas():
    r = api_get("/reservas")
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template("reservas.html", reservas=r.json() if r.status_code == 200 else [])


@app.route("/reservas/<int:reserva_id>/<accion>", methods=["POST"])
@login_required
def reserva_accion(reserva_id, accion):
    if accion not in ("confirmar", "cancelar"):
        flash("Acción no válida.", "error")
        return redirect(url_for("reservas"))
    r = api_post(f"/reservas/{reserva_id}/{accion}", {})
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 200:
        flash(f"Reserva {'confirmada' if accion == 'confirmar' else 'cancelada'}.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo completar la acción."), "error")
    return redirect(url_for("reservas"))


# ----------------------------------------------------------------------
# Estadísticas
# ----------------------------------------------------------------------
@app.route("/estadisticas")
@login_required
def estadisticas():
    torneo_id = request.args.get("torneo_id", type=int)
    sufijo = f"?torneo_id={torneo_id}" if torneo_id else ""

    rt = api_get("/torneos")
    if rt.status_code == 401:
        return _sesion_expirada()
    lista_torneos = rt.json() if rt.status_code == 200 else []

    rg = api_get(f"/estadisticas/goleadores{sufijo}")
    rc = api_get(f"/estadisticas/tarjetas{sufijo}")
    return render_template(
        "estadisticas.html",
        torneos=lista_torneos,
        torneo_id=torneo_id,
        goleadores=rg.json() if rg.status_code == 200 else [],
        tarjetas=rc.json() if rc.status_code == 200 else [],
    )


# ----------------------------------------------------------------------
# Solicitudes de entrenador/árbitro (revisión del admin)
# ----------------------------------------------------------------------
@app.route("/solicitudes")
@login_required
def solicitudes():
    r = api_get("/solicitudes", estado=request.args.get("estado", "pendiente"))
    if r.status_code == 401:
        return _sesion_expirada()
    return render_template(
        "solicitudes.html",
        solicitudes=r.json() if r.status_code == 200 else [],
        estado=request.args.get("estado", "pendiente"),
    )


@app.route("/solicitudes/<int:solicitud_id>/documento")
@login_required
def solicitud_documento(solicitud_id):
    # El documento está protegido por token; el panel lo descarga con la sesión
    # del admin y lo reenvía al navegador.
    resp = requests.get(
        f"{API_URL}/solicitudes/{solicitud_id}/documento",
        headers=_headers(), timeout=TIMEOUT,
    )
    if resp.status_code == 401:
        return _sesion_expirada()
    if resp.status_code != 200:
        flash("No se pudo abrir el documento.", "error")
        return redirect(url_for("solicitudes"))
    return Response(resp.content, content_type=resp.headers.get("Content-Type", "application/octet-stream"))


@app.route("/solicitudes/<int:solicitud_id>/aceptar", methods=["POST"])
@login_required
def solicitud_aceptar(solicitud_id):
    r = api_post(f"/solicitudes/{solicitud_id}/aceptar", {})
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 200:
        flash("Solicitud aceptada. Se envió un correo con la contraseña temporal.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo aceptar la solicitud."), "error")
    return redirect(url_for("solicitudes"))


@app.route("/solicitudes/<int:solicitud_id>/rechazar", methods=["POST"])
@login_required
def solicitud_rechazar(solicitud_id):
    r = api_post(f"/solicitudes/{solicitud_id}/rechazar", {"motivo": request.form.get("motivo", "").strip() or None})
    if r.status_code == 401:
        return _sesion_expirada()
    if r.status_code == 200:
        flash("Solicitud rechazada.", "ok")
    else:
        flash(_detalle_error(r, "No se pudo rechazar la solicitud."), "error")
    return redirect(url_for("solicitudes"))


# ----------------------------------------------------------------------
def _sesion_expirada():
    session.clear()
    flash("Tu sesión expiró. Inicia sesión de nuevo.", "error")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
