"""
Datos de prueba (seed).

Inserta lo minimo para no desarrollar contra una base vacia: los 4 roles,
una sede de ejemplo y un usuario de cada rol CON contrasena real (hasheada),
para poder iniciar sesion en el panel y la app.

Ejecutar DESPUES de aplicar las migraciones, desde dentro del contenedor:
    docker compose exec api python -m app.seed

Es idempotente: si los roles/usuarios ya existen, no los duplica.

Credenciales que crea (solo para desarrollo):
    superadmin -> superadmin@demo.com / admin1234
    entrenador -> entrenador@demo.com / demo1234
    arbitro    -> arbitro@demo.com    / demo1234
    jugador    -> jugador@demo.com    / demo1234
"""
from app.database import SessionLocal
from app import models
from app.security import hash_password

ROLES = ["jugador", "entrenador", "arbitro", "superadmin"]

# Contrasenas de DESARROLLO (cambiar/eliminar en produccion)
PASSWORDS = {
    "superadmin": "admin1234",
    "entrenador": "demo1234",
    "arbitro": "demo1234",
    "jugador": "demo1234",
}


def run():
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

        # Una sede de ejemplo
        if not db.query(models.Sede).first():
            db.add(models.Sede(nombre="Sede Central", ciudad="Pachuca", direccion="Av. Principal 100"))

        # Un usuario por rol con contrasena real (si aun no existen)
        for nombre_rol, rol in roles_por_nombre.items():
            correo = f"{nombre_rol}@demo.com"
            if not db.query(models.Usuario).filter_by(correo=correo).first():
                db.add(models.Usuario(
                    rol_id=rol.id,
                    nombre=f"Demo {nombre_rol}",
                    correo=correo,
                    password_hash=hash_password(PASSWORDS[nombre_rol]),
                ))

        db.commit()

        # Un equipo de ejemplo para el entrenador demo (con plantilla)
        entrenador = db.query(models.Usuario).filter_by(correo="entrenador@demo.com").first()
        if entrenador and not db.query(models.Equipo).filter_by(entrenador_id=entrenador.id).first():
            eq = models.Equipo(
                entrenador_id=entrenador.id, nombre="Halcones FC",
                color="Rojo / Blanco", categoria="Liga A",
            )
            db.add(eq)
            db.flush()
            plantilla = [
                ("J. Ramírez", "Delantero", 9),
                ("L. González", "Portero", 1),
                ("M. Torres", "Defensa", 4),
                ("D. Soto", "Medio", 8),
            ]
            for nombre, posicion, dorsal in plantilla:
                db.add(models.JugadorEquipo(equipo_id=eq.id, nombre=nombre, posicion=posicion, dorsal=dorsal))
            db.commit()

            # Torneo activo + equipo rival + partido programado (demo para árbitro/entrenador)
            admin = db.query(models.Usuario).filter_by(correo="superadmin@demo.com").first()
            arbitro = db.query(models.Usuario).filter_by(correo="arbitro@demo.com").first()
            sede = db.query(models.Sede).first()
            if admin and not db.query(models.Torneo).filter_by(nombre="Liga Municipal A").first():
                torneo = models.Torneo(
                    nombre="Liga Municipal A", sede_id=sede.id if sede else None,
                    tipo="Liga", estado="en_curso", descripcion="Torneo de exhibición.",
                )
                db.add(torneo)
                rival = models.Equipo(entrenador_id=admin.id, nombre="Tigres FC", categoria="Liga A")
                db.add(rival)
                db.flush()
                from datetime import datetime, timedelta
                db.add(models.Partido(
                    torneo_id=torneo.id, equipo_local_id=eq.id, equipo_visitante_id=rival.id,
                    arbitro_id=arbitro.id if arbitro else None,
                    fecha_hora=datetime.now() + timedelta(days=2), estado="programado",
                ))
                db.commit()

        print("Seed completado.")
        print("  superadmin@demo.com / admin1234")
        print("  entrenador@demo.com / demo1234")
        print("  arbitro@demo.com    / demo1234")
        print("  jugador@demo.com    / demo1234")
    finally:
        db.close()


if __name__ == "__main__":
    run()
