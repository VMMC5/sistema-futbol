# Imagen base ligera con Python 3.12
FROM python:3.12-slim

# Evita archivos .pyc y muestra los logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias del sistema necesarias para psycopg2 (driver de PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Instalar dependencias primero (mejor uso de la caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

EXPOSE 8000

# El comando real lo define docker-compose (con --reload para desarrollo).
# Este CMD es el valor por defecto si se corre el contenedor solo.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
