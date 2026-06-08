# Imagen base ligera con Python 3.12
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# En desarrollo, docker-compose lo corre con --debug.
CMD ["flask", "--app", "app.app", "run", "--host", "0.0.0.0", "--port", "5000"]
