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
        print("Seed completado.")
        print("  superadmin@demo.com / admin1234")
        print("  entrenador@demo.com / demo1234")
        print("  arbitro@demo.com    / demo1234")
        print("  jugador@demo.com    / demo1234")
    finally:
        db.close()


if __name__ == "__main__":
    run()
