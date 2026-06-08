# Sistema Integral de Administración de Canchas y Torneos de Fútbol

Plataforma web y móvil para administrar canchas, sedes, torneos, partidos, horarios y usuarios.

## Stack

| Parte           | Tecnología              | Puerto (local)        |
|-----------------|-------------------------|-----------------------|
| API / Backend   | Python + FastAPI        | http://localhost:8000 |
| Panel web admin | Python + Flask          | http://localhost:5000 |
| App móvil       | React Native + Expo     | Expo Go (QR)          |
| Base de datos   | PostgreSQL 16           | 5432                  |

La API expone su documentación interactiva en **http://localhost:8000/docs**.

## Estructura

```
sistema-torneos/
├── docker-compose.yml     # levanta DB + API + Web con un comando
├── .env.example           # plantilla de variables (copiar a .env)
├── .gitignore
├── api/                   # Backend FastAPI
├── web/                   # Panel admin Flask
├── mobile/                # App React Native + Expo
└── docs/                  # Documentación (análisis, diseño, seguridad)
```

## Requisitos previos

- **Docker Desktop** (en Windows: con WSL 2 activado).
- **Node LTS** + app **Expo Go** en el teléfono (solo para la app móvil).
- En **Windows**: clonar y trabajar **dentro de WSL** (`~/proyectos/...`), no en `C:\Users\...`.

## Arranque rápido

```bash
# 1. Clonar
git clone git@github.com:tu-org/sistema-torneos.git
cd sistema-torneos

# 2. Crear tu archivo de entorno a partir de la plantilla
cp .env.example .env
#    -> rellena .env con las credenciales que te pase el equipo

# 3. Levantar base de datos + API + panel web
docker compose up --build
```

Verifica que todo arrancó:
- API: abre http://localhost:8000/health → debe responder `base_de_datos: ok`.
- Panel web: abre http://localhost:5000 → debe mostrar el estado de la API.

Para detener todo: `docker compose down` (los datos de la BD se conservan).

## App móvil (en otra terminal)

```bash
cd mobile
npm install
npx expo start
```

Escanea el QR con **Expo Go**. La app apunta a la API mediante una variable
de entorno propia del móvil (la IP local de la máquina que corre la API).

> El móvil **no** corre en Docker, por eso se levanta por separado.

## Flujo de trabajo (Git)

Nadie trabaja directo en `main`. Por cada tarea:

```bash
git checkout main && git pull
git checkout -b feat/nombre-tarea
# ...trabajar y hacer commits pequeños...
git push -u origin feat/nombre-tarea
```

Luego se abre un **Pull Request** hacia `main`, lo revisa un compañero y se mezcla.
Convención de ramas: `feat/...`, `fix/...`, `docs/...`.

## Variables de entorno

Las credenciales viven en `.env` (que **nunca** se sube). La plantilla pública
es `.env.example`. Nunca escribas contraseñas, llaves de pago o tokens
directamente en el código.
