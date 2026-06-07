"""
Punto de entrada del panel web administrativo (Flask).

Esqueleto mínimo y funcional: arranca, muestra una página de inicio
y comprueba que puede comunicarse con la API. Aquí vivirá toda la
gestión del administrador (sedes, torneos, canchas, usuarios, pagos, reportes).
"""
import os

import requests
from flask import Flask

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")

# URL de la API. Dentro de la red de docker-compose, el host es "api".
API_URL = os.getenv("API_URL", "http://api:8000")


@app.route("/")
def inicio():
    # Intenta contactar a la API para mostrar su estado
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        estado_api = r.json()
    except Exception as e:  # noqa: BLE001
        estado_api = {"error": str(e)}

    return f"""
    <h1>Panel Admin — Sistema de Torneos 🟢</h1>
    <p>El panel Flask está funcionando.</p>
    <p>Estado de la API: <code>{estado_api}</code></p>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
