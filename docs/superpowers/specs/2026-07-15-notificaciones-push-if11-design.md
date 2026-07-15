# Notificaciones push (IF-11) — Diseño

**Fecha:** 2026-07-15
**Estado:** Aprobado, pendiente de plan de implementación
**Requisito:** IF-11 (notificaciones push), pendiente desde el diagnóstico Tech Lead.

## Objetivo

Añadir notificaciones push reales a la app móvil, construyendo **encima** del
sistema actual (notificación en BD + polling por `useFocusEffect`), sin
retirarlo. El push es un canal extra que se dispara desde un **único helper
central**; el polling queda como respaldo (si el push no llega, la
notificación sigue estando en BD).

## Estado actual (punto de partida)

- Modelo `Notificacion(id, usuario_id, titulo, mensaje, leida, creada_en)`.
- Router `notificaciones.py`: `GET ""`, `POST /marcar-leidas`, `DELETE /{id}`.
- Las notificaciones se crean hoy en 3 sitios, **sin helper central**:
  - `pagos_service._notificar(...)` (pagos confirmados / en revisión).
  - `equipos.py` (invitación a equipo).
  - `seed.py` (datos de arranque).
- Móvil: `NotificationsScreen` lee `/notificaciones` + `/invitaciones/mias`
  por polling al enfocar la pantalla.
- `httpx==0.28.1` ya es dependencia del backend.
- Baseline Alembic único: `ac4f76d969b7` (`down_revision=None`).

## Alcance (decisiones tomadas)

- **Disparadores:** todos los eventos que hoy crean notificaciones, unificados
  en un helper central (así cada aviso existente y futuro también sale como
  push). `seed.py` queda fuera (no envía push).
- **Transporte:** Expo Push Service (`https://exp.host/--/api/v2/push/send`).
- **Entrega:** vía **FastAPI `BackgroundTasks`** (no bloquea el request).
  Best-effort: un fallo de push nunca rompe la acción ni el registro en BD.
- **Verificación:** backend end-to-end con la Expo API mockeada (tests). El
  móvil se implementa completo y se valida que compila; el demo en dispositivo
  real queda documentado como paso manual (requiere build EAS del usuario).

## Backend

### Modelo `DispositivoPush`

Tabla `dispositivos_push`:

| Columna     | Tipo                     | Notas                          |
|-------------|--------------------------|--------------------------------|
| id          | Integer PK               |                                |
| usuario_id  | Integer FK usuarios.id   | not null                       |
| token       | String, **unique**       | Expo push token                |
| plataforma  | String, nullable         | "ios" / "android"              |
| creado_en   | DateTime(timezone=True)  | server_default=now()           |

Un usuario puede tener varios dispositivos (varias filas). `relationship` en
`Usuario`. **Nueva migración Alembic** con `down_revision='ac4f76d969b7'`.

### Servicio `app/notificaciones_service.py`

- `crear_notificacion(db, usuario_id, titulo, mensaje, background_tasks)`:
  - Inserta la fila `Notificacion` (comportamiento actual).
  - `background_tasks.add_task(enviar_push, usuario_id, titulo, mensaje)`.
  - Es la **única** puerta de entrada para crear notificaciones (salvo seed).
- `enviar_push(usuario_id, titulo, mensaje)` — **tarea autónoma**:
  - Abre su **propia** sesión (`SessionLocal`), porque la del request ya está
    cerrada cuando la tarea corre tras la respuesta.
  - Consulta los tokens del usuario; si no hay, termina.
  - `POST` a la Expo Push API con `httpx` (timeout corto) enviando
    `[{to, title, body, sound}]`.
  - Procesa la respuesta: los tokens con error `DeviceNotRegistered` se
    **eliminan** de la tabla.
  - **Best-effort:** todo envuelto en try/except; nunca lanza.

### Refactor de los 3 sitios actuales

- `pagos_service._notificar` → delega en `crear_notificacion`.
- `equipos.py` (invitación) → usa `crear_notificacion`.
- `seed.py` → se queda con inserción directa de `models.Notificacion` (sin push).

### Propagación de `BackgroundTasks`

`BackgroundTasks` se inyecta en los **handlers de ruta** y se propaga hacia
abajo hasta el helper:

- `equipos.py`: el handler de invitación recibe `background_tasks: BackgroundTasks`.
- `pagos.py` + `pagos_service.py`: los handlers y las funciones de servicio que
  terminan llamando a `_notificar` reciben y pasan `background_tasks`.

### Endpoints nuevos (router `notificaciones`, auth requerido)

- `POST /notificaciones/dispositivos` — registra/actualiza el token del usuario
  actual. **Idempotente**: si el token ya existe (de otro usuario o el mismo),
  se reasigna al usuario actual y se actualiza `plataforma`.
  - Schema `DispositivoRegistro(token: str, plataforma: str | None)`; `token`
    no vacío.
- `DELETE /notificaciones/dispositivos?token=<token>` — borra ese token del
  usuario actual (en logout). El token va como query param.

## Móvil

### Módulo `mobile/src/push.js`

- `registrarParaPush()`:
  - Solo en dispositivo físico (`expo-device`).
  - Pide permisos (`expo-notifications`); si se conceden, obtiene el token con
    `getExpoPushTokenAsync({ projectId })` (projectId desde
    `Constants.expoConfig.extra.eas.projectId`).
  - `POST /notificaciones/dispositivos` con el token y la plataforma.
- `configurarManejadores(navigation)`:
  - Handler de primer plano: muestra la notificación entrante.
  - Listener de respuesta: al tocar la notificación, navega a la pantalla de
    Avisos (Notifications).
- `desregistrar()`: `DELETE /notificaciones/dispositivos` con el token local.

### Integración

- `auth.js`: llamar `registrarParaPush()` tras un login exitoso y en el
  arranque cuando ya hay sesión; llamar `desregistrar()` en `logout()` antes de
  borrar el token de sesión.
- Montar `configurarManejadores` en la raíz de la app.

### Configuración

- Añadir `expo-notifications` y `expo-device` a `package.json`.
- `app.json`: añadir `extra.eas.projectId` como **placeholder documentado**
  para que el usuario lo rellene en su build EAS. Sin projectId,
  `registrarParaPush()` no obtiene token (se degrada silenciosamente, no rompe).

## Pruebas (backend, Expo mockeado)

`TestClient` ejecuta las `BackgroundTasks` tras la respuesta, así que los
efectos del push son observables en el test mockeando la llamada HTTP a Expo.

- Registro de dispositivo: alta, reasignación de token existente, borrado.
- `crear_notificacion` inserta la fila **y** encola `enviar_push` (verificable
  vía monkeypatch del envío o del cliente httpx).
- `enviar_push` elimina los tokens que devuelven `DeviceNotRegistered`
  (respuesta Expo mockeada).
- Un fallo de la Expo API (excepción o timeout) **no** rompe la creación de la
  notificación ni el request que la originó.
- Móvil: se valida que `push.js` y los archivos tocados compilan con
  `babel-preset-expo`. El demo en teléfono real queda documentado.

## Fuera de alcance (YAGNI)

- Deep-linking a pantallas concretas (el tap solo abre Avisos).
- Badges de conteo en el icono de la app.
- Agrupación/categorías/canales de notificación.
- Configurar EAS ahora (el usuario lo hace para su build).

## Riesgos / notas

- El push refleja la notificación aunque, en un caso extremo, la transacción
  externa haga rollback después de encolar la tarea (la fila no persistiría pero
  el push ya se envió). Es un caso límite aceptable a este volumen.
- Expo Go (SDK 53+) no soporta push remoto: el demo real exige un development
  build. El backend y el móvil quedan listos; solo el paso de build es del
  usuario.
