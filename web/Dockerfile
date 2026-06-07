# Imagen base ligera con Python 3.12
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias del sistema para psycopg2 (driver de PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Valor por defecto. En desarrollo, docker-compose lo corre con --debug.
# En producción se usaría gunicorn (ver comentario en requirements.txt).
CMD ["flask", "--app", "app.app", "run", "--host", "0.0.0.0", "--port", "5000"]
