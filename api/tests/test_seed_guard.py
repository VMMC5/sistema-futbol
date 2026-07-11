"""
Pruebas de la barrera de producción del seed.

El seed crea usuarios demo con contraseñas conocidas, así que no debe correr en
producción. Aquí se comprueba la barrera (_verificar_entorno) y la resolución de
contraseñas desde el entorno, sin tocar la base de datos.
"""
import pytest

from app import seed

# Todas las variables que la barrera mira; se limpian antes de cada prueba para
# que el entorno real del desarrollador no altere el resultado.
VARIABLES = [
    "APP_ENV",
    "SEED_ALLOW_IN_PROD",
    "SEED_PASSWORD_PLANTEL",
] + [f"SEED_PASSWORD_{rol.upper()}" for rol in seed.ROLES]


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)


def _passwords_completas(monkeypatch, valor="Secreta-De-Prod-123"):
    for rol in seed.ROLES:
        monkeypatch.setenv(f"SEED_PASSWORD_{rol.upper()}", valor)
    monkeypatch.setenv("SEED_PASSWORD_PLANTEL", valor)


def test_en_desarrollo_no_hay_barrera():
    """Sin APP_ENV (o en development) el seed corre con normalidad."""
    seed._verificar_entorno()  # no debe lanzar


def test_en_produccion_aborta(monkeypatch):
    """Con APP_ENV=production el seed se niega a correr."""
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(SystemExit) as exc:
        seed._verificar_entorno()

    assert "SEED_ALLOW_IN_PROD" in str(exc.value)


def test_en_produccion_forzado_sin_passwords_aborta(monkeypatch):
    """Forzarlo no basta: en producción no se usan las contraseñas por defecto."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SEED_ALLOW_IN_PROD", "true")

    with pytest.raises(SystemExit) as exc:
        seed._verificar_entorno()

    mensaje = str(exc.value)
    assert "SEED_PASSWORD_SUPERADMIN" in mensaje
    assert "SEED_PASSWORD_PLANTEL" in mensaje


def test_en_produccion_forzado_con_passwords_pasa(monkeypatch):
    """Con el escape explícito y todas las contraseñas, el seed puede correr."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SEED_ALLOW_IN_PROD", "true")
    _passwords_completas(monkeypatch)

    seed._verificar_entorno()  # no debe lanzar


def test_passwords_por_defecto_en_desarrollo():
    """Sin variables, se usan las contraseñas demo de desarrollo."""
    assert seed._passwords() == seed.PASSWORDS_DEV
    assert seed._password_plantel() == seed.PASSWORD_PLANTEL_DEV


def test_passwords_se_toman_del_entorno(monkeypatch):
    """Las variables SEED_PASSWORD_* tienen prioridad sobre los valores demo."""
    monkeypatch.setenv("SEED_PASSWORD_SUPERADMIN", "otra-clave")
    monkeypatch.setenv("SEED_PASSWORD_PLANTEL", "clave-plantel")

    passwords = seed._passwords()

    assert passwords["superadmin"] == "otra-clave"
    # Los roles sin variable siguen con su valor de desarrollo.
    assert passwords["jugador"] == seed.PASSWORDS_DEV["jugador"]
    assert seed._password_plantel() == "clave-plantel"
