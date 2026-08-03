# Iniciar torneo: calendario automático y asignación de árbitros

**Fecha:** 2026-08-02
**Estado:** diseño validado en conversación (incluida la corrección de byes del usuario)

## Objetivo

El superadmin inicia un torneo desde el panel web con un botón: el torneo pasa
de `programado` a `en_curso` y el sistema genera el calendario según el tipo
(liga = ida y vuelta; eliminación directa = llaves con byes). Después puede
asignar árbitro a cada partido desde un listado de **árbitros disponibles**
(sin otro partido en la misma fecha y hora).

## Punto de partida (ya existe — no reimplementar)

- `Torneo.tipo` (texto libre hoy) y `Torneo.estado` (`programado/en_curso/finalizado`).
- `Inscripcion` con estado `aceptada` (la fuente de los participantes).
- `POST /partidos` y `PUT /partidos/{id}` (superadmin) con validaciones y
  notificaciones al árbitro/entrenadores (PR #28).
- Panel: `torneos.html` (lista), `partido_detalle.html`, `torneo_nuevo.html`.

## Modelo

- **Nueva columna `partidos.jornada`** (Integer, nullable): nº de jornada en
  liga, nº de ronda en eliminación. Migración pequeña sobre el baseline; los
  partidos existentes quedan `NULL`.

## Normalización del tipo

- `tipo` se normaliza (minúsculas, sin acentos, trim) y se reconocen dos
  valores: **`liga`** y **`eliminacion directa`**. Otro valor → 400 al iniciar.
- `torneo_nuevo.html`: el campo pasa de texto libre a `<select>` con esos dos
  valores canónicos.

## API (todo superadmin salvo la regla de finalizar)

### `POST /torneos/{id}/iniciar` — body `{primera_fecha: date, hora_base: "HH:MM"}`

Validaciones (en orden): torneo existe (404) → estado `programado` (409) →
tipo reconocido (400) → ≥2 inscripciones aceptadas (400).

Efectos: crea los partidos (estado `programado`, sin árbitro, `jornada`
numerada desde 1) y pone el torneo `en_curso`. Fechas: `primera_fecha` +
`hora_base` interpretadas como UTC (igual que la creación manual por Swagger);
partidos de la misma jornada escalonados **+2 h** por partido. Canchas: las de
la **sede del torneo** rotando (ordenadas por id); sede sin canchas →
`cancha_id` NULL.

- **Liga**: round-robin por método del círculo, **ida y vuelta**: la vuelta
  espeja cada jornada de ida con la localía invertida. `n` equipos → `2(n-1)`
  jornadas (impar: `2n` jornadas con descanso por jornada), una por semana.
- **Eliminación directa (ronda 1)**: `byes = siguiente_potencia_de_2(n) − n`,
  elegidos **al azar**; pasan directo a la ronda 2. El resto se baraja y se
  empareja: `(n − byes) / 2` partidos, todos el día elegido escalonados +2 h.
  Casos: n=6 → 2 byes y 2 partidos (ronda 2 = 4) ✓; n potencia de 2 → 0 byes;
  n=2 → final directa. El azar se inyecta (parámetro/función) para poder
  probarlo determinista.

Notificaciones: **una por entrenador** con inscripción aceptada ("Torneo
iniciado: revisa tu calendario"), vía `notificaciones_service` (BD + push
best-effort). NO se emite el aviso por-partido de `POST /partidos` (serían
cientos).

### `POST /torneos/{id}/siguiente-ronda` — body `{fecha: date, hora_base}`

Solo eliminación (400 si liga). Validaciones: torneo `en_curso` (409), todos
los partidos de la ronda más alta `finalizado` (409 con cuántos faltan).
Ganador de cada partido = mayor marcador (el empate es imposible, ver regla
abajo). Participantes de la nueva ronda = ganadores + byes de ronda 1 (si la
ronda más alta es la 1). **Los byes se derivan, no se almacenan**: equipos con
inscripción aceptada que no aparecen en ningún partido de la ronda 1. Los cruces **se sortean de nuevo cada ronda** (no hay
llave fija — decisión consciente, torneo informal). Si solo queda **un**
ganador: no crea partidos, marca el torneo `finalizado` y responde el campeón.

### `GET /partidos/{id}/arbitros-disponibles`

Árbitros (rol `arbitro`, activos) **sin otro partido no-`finalizado` con la
misma `fecha_hora` exacta** (la regla del usuario; sin ventanas de traslape,
YAGNI). Partido sin `fecha_hora` → todos disponibles. Incluye al árbitro ya
asignado al propio partido (para mostrarlo seleccionado).

### Reglas nuevas en endpoints existentes

- **Asignar árbitro con choque** (en `POST /partidos` y `PUT /partidos/{id}`):
  si el árbitro tiene otro partido no-`finalizado` con la misma `fecha_hora`
  → **409** "El árbitro ya tiene un partido a esa hora". La barrera real es el
  servidor; el dropdown solo filtra.
- **Finalizar empatado en eliminación**: en el endpoint de finalizar partido,
  si el torneo (normalizado) es `eliminacion directa` y el marcador va
  empatado → **409** "En eliminación directa el partido no puede terminar
  empatado" (el árbitro registra el desempate como gol y reintenta).

## Panel web

- **`torneos.html`**: en filas `programado`, botón **"Iniciar torneo"** →
  formulario chico (`torneo_iniciar.html`: primera fecha + hora base) → POST →
  flash "Torneo iniciado: N partidos creados". En filas eliminación
  `en_curso`, botón **"Siguiente ronda"** (mismo formulario). Errores de la
  API → flash con el `detail` (patrón `_detalle_error`).
- **`partido_detalle.html`**: sección "Asignar árbitro": nombre del árbitro
  actual + `<select>` alimentado por `arbitros-disponibles` + botón que hace
  `PUT /partidos/{id}` con el elegido.
- **`torneo_nuevo.html`**: `tipo` como `<select>` (Liga / Eliminación directa).

## Fuera de alcance (a propósito)

Editar fechas de partidos desde el panel; finalizar torneos de liga (manual);
registro de penales; bracket visual; ventanas de traslape horario del árbitro.

## Tests

- **Generador liga** (función pura): n par e impar, 2(n-1) jornadas, cada par
  se enfrenta exactamente 2 veces con localía invertida, fechas semanales y
  escalonado +2 h, rotación de canchas.
- **Generador eliminación** (azar inyectado): n=6 → 2 byes + 2 partidos; n=8 →
  0 byes; n=2 → final; byes solo en ronda 1.
- **`iniciar`**: 409 si no está `programado`, 400 tipo/inscripciones,
  partidos con `jornada`, torneo `en_curso`, UNA notificación por entrenador.
- **`siguiente-ronda`**: 409 con ronda incompleta, cruces de ganadores+byes,
  campeón → torneo `finalizado`, 400 en liga.
- **Árbitros**: listado filtra el choque exacto; asignar con choque → 409
  (en crear y en actualizar); sin `fecha_hora` no filtra.
- **Finalizar empatado** en eliminación → 409; en liga sigue permitido.
- Panel: validación visual del usuario (sin navegador headless).
