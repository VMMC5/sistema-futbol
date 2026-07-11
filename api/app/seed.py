"""
Datos de prueba (seed).

Inserta lo minimo para no desarrollar contra una base vacia: los 4 roles,
una sede de ejemplo y un usuario de cada rol CON contrasena real (hasheada),
para poder iniciar sesion en el panel y la app.

Ejecutar DESPUES de aplicar las migraciones, desde dentro del contenedor:
    docker compose exec api python -m app.seed

Es idempotente: si los roles/usuarios ya existen, no los duplica.

SEGURIDAD: este script crea usuarios con contrasenas conocidas, asi que NO debe
correr en produccion. Si APP_ENV=production, aborta (ver _verificar_entorno).
Para el caso legitimo de sembrar los roles base en produccion hay que pedirlo
explicitamente con SEED_ALLOW_IN_PROD=true Y dar una contrasena propia en cada
SEED_PASSWORD_*; sin eso no se usa ningun valor por defecto.

Variables de entorno:
    APP_ENV               -> "production" activa la barrera. Por defecto "development".
    SEED_ALLOW_IN_PROD    -> "true" permite correr el seed aun en produccion.
    SEED_PASSWORD_<ROL>   -> contrasena de cada usuario demo (SUPERADMIN, ENTRENADOR,
                             ARBITRO, JUGADOR).
    SEED_PASSWORD_PLANTEL -> contrasena de los jugadores de las plantillas demo.

Credenciales por defecto (SOLO desarrollo):
    superadmin -> superadmin@demo.com / admin1234
    entrenador -> entrenador@demo.com / demo1234
    arbitro    -> arbitro@demo.com    / demo1234
    jugador    -> jugador@demo.com    / demo1234
"""
import os

from app.database import SessionLocal
from app import models
from app.security import hash_password

ROLES = ["jugador", "entrenador", "arbitro", "superadmin"]

# Contrasenas de DESARROLLO. Solo se usan fuera de produccion: la barrera de
# _verificar_entorno() exige contrasenas explicitas si se fuerza el seed en prod.
PASSWORDS_DEV = {
    "superadmin": "admin1234",
    "entrenador": "demo1234",
    "arbitro": "demo1234",
    "jugador": "demo1234",
}
PASSWORD_PLANTEL_DEV = "demo1234"

# Las contrasenas de las plantillas demo comparten esta variable.
_ENV_PLANTEL = "SEED_PASSWORD_PLANTEL"


def _en_produccion() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def _es_verdadero(valor: str) -> bool:
    return (valor or "").strip().lower() in ("true", "1", "yes")


def _verificar_entorno() -> None:
    """Impide sembrar credenciales demo en produccion.

    Fuera de produccion no hace nada. En produccion aborta, salvo que se pida
    explicitamente con SEED_ALLOW_IN_PROD=true; incluso entonces, exige que cada
    contrasena venga del entorno para no crear usuarios con claves publicas.
    """
    if not _en_produccion():
        return

    if not _es_verdadero(os.getenv("SEED_ALLOW_IN_PROD", "")):
        raise SystemExit(
            "Seed abortado: APP_ENV=production y este script crea usuarios demo "
            "con contrasenas conocidas. Si de verdad necesitas sembrar los roles "
            "base en produccion, define SEED_ALLOW_IN_PROD=true y una contrasena "
            "propia en cada SEED_PASSWORD_*."
        )

    requeridas = [f"SEED_PASSWORD_{rol.upper()}" for rol in ROLES] + [_ENV_PLANTEL]
    faltantes = [nombre for nombre in requeridas if not os.getenv(nombre)]
    if faltantes:
        raise SystemExit(
            "Seed abortado: en produccion no se usan las contrasenas por defecto. "
            "Faltan estas variables: " + ", ".join(faltantes)
        )


def _passwords() -> dict:
    """Contrasena de cada usuario demo: del entorno, o el valor de desarrollo."""
    return {
        rol: os.getenv(f"SEED_PASSWORD_{rol.upper()}") or PASSWORDS_DEV[rol]
        for rol in ROLES
    }


def _password_plantel() -> str:
    return os.getenv(_ENV_PLANTEL) or PASSWORD_PLANTEL_DEV


def run():
    _verificar_entorno()
    passwords = _passwords()
    password_plantel = _password_plantel()

    db = SessionLocal()
    try:
        # Roles (idempotente)
        roles_por_nombre = {}
        for nombre in ROLES:
            rol = db.query(models.Rol).filter_by(nombre=nombre).first()
            if not rol:
                rol = models.Rol(nombre=nombre)
                db.add(rol)
                db.flush()
            roles_por_nombre[nombre] = rol

        # Una sede de ejemplo con canchas (para reservas)
        if not db.query(models.Sede).first():
            sede_demo = models.Sede(nombre="Sede Central", ciudad="Pachuca", direccion="Av. Principal 100")
            db.add(sede_demo)
            db.flush()
            db.add_all([
                models.Cancha(sede_id=sede_demo.id, nombre="Cancha 1", tipo="futbol 5", precio_hora=200),
                models.Cancha(sede_id=sede_demo.id, nombre="Cancha 2", tipo="futbol 7", precio_hora=250),
                models.Cancha(sede_id=sede_demo.id, nombre="Cancha 3", tipo="futbol 7", precio_hora=250),
            ])

        # Un usuario por rol con contrasena real (si aun no existen)
        for nombre_rol, rol in roles_por_nombre.items():
            correo = f"{nombre_rol}@demo.com"
            if not db.query(models.Usuario).filter_by(correo=correo).first():
                db.add(models.Usuario(
                    rol_id=rol.id,
                    nombre=f"Demo {nombre_rol}",
                    correo=correo,
                    password_hash=hash_password(passwords[nombre_rol]),
                ))

        db.commit()

        # ---- Datos demo (equipos con jugadores registrados, invitación, partido) ----
        entrenador = db.query(models.Usuario).filter_by(correo="entrenador@demo.com").first()
        admin = db.query(models.Usuario).filter_by(correo="superadmin@demo.com").first()
        arbitro = db.query(models.Usuario).filter_by(correo="arbitro@demo.com").first()
        rol_jugador = roles_por_nombre["jugador"]
        sede = db.query(models.Sede).first()

        def jugador_demo(nombre, correo):
            u = db.query(models.Usuario).filter_by(correo=correo).first()
            if not u:
                u = models.Usuario(
                    rol_id=rol_jugador.id, nombre=nombre, correo=correo,
                    password_hash=hash_password(password_plantel),
                )
                db.add(u)
                db.flush()
            return u

        if entrenador and not db.query(models.Equipo).filter_by(entrenador_id=entrenador.id).first():
            eq = models.Equipo(entrenador_id=entrenador.id, nombre="Halcones FC",
                               color="Rojo / Blanco", categoria="Liga A")
            rival = models.Equipo(entrenador_id=admin.id, nombre="Tigres FC", categoria="Liga A")
            db.add_all([eq, rival])
            db.flush()

            # Plantilla de Halcones (jugadores registrados)
            halcones = [
                ("Juan Ramírez", "juan@demo.com", "Delantero", 9),
                ("Luis González", "luis@demo.com", "Portero", 1),
                ("Mario Torres", "mario@demo.com", "Defensa", 4),
                ("Diego Soto", "diego@demo.com", "Medio", 8),
            ]
            for nombre, correo, posicion, dorsal in halcones:
                u = jugador_demo(nombre, correo)
                db.add(models.JugadorEquipo(equipo_id=eq.id, jugador_id=u.id, posicion=posicion, dorsal=dorsal))

            # Plantilla de Tigres
            tigres = [
                ("Pedro Vargas", "pedro@demo.com", "Delantero", 11),
                ("Raúl Mena", "raul@demo.com", "Portero", 12),
                ("Saúl Díaz", "saul@demo.com", "Defensa", 3),
            ]
            for nombre, correo, posicion, dorsal in tigres:
                u = jugador_demo(nombre, correo)
                db.add(models.JugadorEquipo(equipo_id=rival.id, jugador_id=u.id, posicion=posicion, dorsal=dorsal))

            # Jugadores disponibles (registrados, sin equipo) para probar la búsqueda
            jugador_demo("Carlos Pérez", "carlos@demo.com")
            jugador_demo("Erik Lara", "erik@demo.com")

            # Invitación pendiente al jugador demo principal (jugador@demo.com)
            jdemo = db.query(models.Usuario).filter_by(correo="jugador@demo.com").first()
            if jdemo:
                db.add(models.InvitacionEquipo(equipo_id=eq.id, jugador_id=jdemo.id))
                db.add(models.Notificacion(
                    usuario_id=jdemo.id, titulo="Invitación a equipo",
                    mensaje="Halcones FC te invitó a unirte al equipo.",
                ))

            # Torneo activo + partido programado (demo para árbitro y entrenador)
            if not db.query(models.Torneo).filter_by(nombre="Liga Municipal A").first():
                torneo = models.Torneo(
                    nombre="Liga Municipal A", sede_id=sede.id if sede else None,
                    tipo="Liga", estado="en_curso", descripcion="Torneo de exhibición.",
                )
                db.add(torneo)
                db.flush()
                from datetime import datetime, timedelta
                db.add(models.Partido(
                    torneo_id=torneo.id, equipo_local_id=eq.id, equipo_visitante_id=rival.id,
                    arbitro_id=arbitro.id if arbitro else None,
                    fecha_hora=datetime.now() - timedelta(minutes=5), estado="programado",
                ))
                # Un segundo partido en el futuro (su botón de iniciar estará bloqueado)
                db.add(models.Partido(
                    torneo_id=torneo.id, equipo_local_id=eq.id, equipo_visitante_id=rival.id,
                    arbitro_id=arbitro.id if arbitro else None,
                    fecha_hora=datetime.now() + timedelta(days=2), estado="programado",
                ))
                db.flush()

                # Un partido YA FINALIZADO con eventos, para mostrar estadísticas del jugador
                juan = db.query(models.Usuario).filter_by(correo="juan@demo.com").first()
                diego = db.query(models.Usuario).filter_by(correo="diego@demo.com").first()
                pedro = db.query(models.Usuario).filter_by(correo="pedro@demo.com").first()
                fin = models.Partido(
                    torneo_id=torneo.id, equipo_local_id=eq.id, equipo_visitante_id=rival.id,
                    arbitro_id=arbitro.id if arbitro else None,
                    fecha_hora=datetime.now() - timedelta(days=3), estado="finalizado",
                    goles_local=2, goles_visitante=1, acta_firmada=True, acta_firmada_en=datetime.now(),
                )
                db.add(fin)
                db.flush()
                if juan and diego and pedro:
                    db.add_all([
                        models.EventoPartido(partido_id=fin.id, equipo_id=eq.id, jugador_id=juan.id,
                                             jugador_secundario_id=diego.id, tipo="gol", subtipo="normal", minuto=23),
                        models.EventoPartido(partido_id=fin.id, equipo_id=eq.id, jugador_id=juan.id,
                                             tipo="gol", subtipo="penal", minuto=58),
                        models.EventoPartido(partido_id=fin.id, equipo_id=eq.id, jugador_id=juan.id,
                                             tipo="tarjeta_amarilla", minuto=70),
                        models.EventoPartido(partido_id=fin.id, equipo_id=rival.id, jugador_id=pedro.id,
                                             tipo="gol", subtipo="normal", minuto=80),
                    ])
                    # Notificaciones demo para el jugador juan@demo.com
                    db.add_all([
                        models.Notificacion(usuario_id=juan.id, titulo="¡Gol registrado!",
                                            mensaje="Tu equipo anotó al min. 23'."),
                        models.Notificacion(usuario_id=juan.id, titulo="Nuevo torneo abierto",
                                            mensaje="Liga Municipal A · inscripciones abiertas."),
                        models.Notificacion(usuario_id=juan.id, titulo="Convocatoria",
                                            mensaje="Próximo partido programado.", leida=True),
                    ])
            db.commit()

        print("Seed completado.")
        # Las credenciales solo se imprimen fuera de produccion: en un servidor
        # real acabarian en los logs.
        if not _en_produccion():
            for rol in ["superadmin", "entrenador", "arbitro", "jugador"]:
                print(f"  {rol}@demo.com / {passwords[rol]}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
