# Autenticación y roles (JWT)

El acceso al sistema se basa en **JWT**: el usuario inicia sesión, recibe un
token, y lo envía en cada petición protegida con la cabecera
`Authorization: Bearer <token>`. El token lleva dentro el id del usuario y su rol.

> Antes de probar, asegúrate de haber corrido el seed (crea los roles base):
> `docker compose exec api python -m app.seed`
> Y de tener un `SECRET_KEY` real en el `.env` (genera uno con `openssl rand -hex 32`).

## Endpoints

| Método | Ruta             | Para qué                                  | Protegida |
|--------|------------------|-------------------------------------------|-----------|
| POST   | `/auth/register` | Registrar un jugador nuevo                | No        |
| POST   | `/auth/login`    | Iniciar sesión y obtener el token         | No        |
| GET    | `/auth/me`       | Ver los datos del usuario autenticado     | Sí        |
| GET    | `/auth/admin-test` | Ejemplo de ruta solo para `superadmin`  | Sí (rol)  |

La forma más cómoda de probarlos es la documentación interactiva en
**http://localhost:8000/docs** (incluye el botón *Authorize* para pegar el token).

## Ejemplo de flujo (con curl)

```bash
# 1. Registrar un jugador
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Ana","correo":"ana@demo.com","password":"claveSegura123"}'

# 2. Iniciar sesión -> devuelve {"access_token":"...","token_type":"bearer"}
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"correo":"ana@demo.com","password":"claveSegura123"}'

# 3. Usar el token en una ruta protegida
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer PEGA_AQUI_EL_TOKEN"
```

## Cómo proteger tus propios endpoints

Cualquier ruta nueva (torneos, reservas, partidos...) se protege añadiendo una
dependencia:

```python
from fastapi import Depends
from app.deps import get_current_user, require_roles
from app import models

# Solo requiere estar autenticado (cualquier rol):
@router.get("/torneos")
def listar_torneos(usuario: models.Usuario = Depends(get_current_user)):
    ...

# Requiere un rol concreto (uno o varios):
@router.post("/torneos")
def crear_torneo(usuario: models.Usuario = Depends(require_roles("superadmin"))):
    ...

@router.post("/partidos/{id}/evento")
def registrar_evento(usuario: models.Usuario = Depends(require_roles("arbitro", "superadmin"))):
    ...
```

## Notas de seguridad (alineado con el documento de seguridad)

- Las contraseñas se guardan **hasheadas con bcrypt**, nunca en texto plano.
- En login, el mensaje de error es el mismo para "correo no existe" y
  "contraseña incorrecta", para no dar pistas a un atacante.
- El `SECRET_KEY` que firma los tokens vive en el `.env`, jamás en el código.
- Toda entrada se valida con esquemas Pydantic antes de tocar la base de datos.
