# Notificaciones para el árbitro y el entrenador

Fecha: 2026-07-31
Estado: aprobado por el usuario (triggers elegidos explícitamente), pendiente de plan

## Problema

La infraestructura de notificaciones existe completa desde el PR #16
(`notificaciones_service.crear_notificacion` inserta en BD **y** encola push a Expo;
la tabla, los endpoints y la pantalla funcionan), pero solo dos eventos la usan:
pagos e invitaciones a equipo. El árbitro y el entrenador no se enteran de nada:
nadie genera sus avisos y sus paneles ni siquiera tienen acceso a la pantalla.

## Triggers elegidos por el usuario

| Rol | Evento | Hoy |
|---|---|---|
| Árbitro | Partido asignado (al crear o reasignar) | Nada |
| Árbitro | Cambio de fecha/hora o cancha de su partido | Nada |
| Árbitro | Partido eliminado | Nada |
| Entrenador | Torneo nuevo abierto | Nada |
| Entrenador | Partido programado/reprogramado/cancelado de su equipo | Nada |
| Entrenador | Resultado de su inscripción | Parcial: "Pago confirmado" al pagador |

## Hallazgos del reconocimiento que fijan el diseño

- `crear_notificacion(db, usuario_id, titulo, mensaje, background_tasks)` es **la
  única puerta** (no hace commit; el caller comete). El push es best-effort y ya
  purga tokens muertos. No hay columna `tipo`: el título es el discriminador (la
  pantalla elige icono por palabra clave del título).
- Los tokens push de entrenador y árbitro **ya se registran** al iniciar sesión
  (`auth.js` es agnóstico al rol). Solo falta generar avisos y dar acceso a la pantalla.
- `crear_partido`/`actualizar_partido`/`eliminar_partido` (superadmin) no notifican
  nada y no reciben `BackgroundTasks`. `actualizar_partido` hace un `setattr` ciego:
  hay que **capturar los valores previos antes del loop** para saber qué cambió.
- `GET /notificaciones` ya filtra por usuario; no hace falta tocar nada ahí.
- `NotificationsScreen` es casi agnóstica al rol: la sección de invitaciones solo se
  pinta si hay filas, y `/invitaciones/mias` devuelve `[]` para cualquier no-jugador
  (filtra por `jugador_id`). La pantalla se **reutiliza tal cual**; lo que falta es
  registrarla con la cabecera de cada panel y ponerle campana a los dos inicios.
- **No existe flujo de rechazo de inscripciones** (nada pone `estado="rechazada"`).
  Decisión del usuario "respetar lo existente": el "resultado" notificable es
  únicamente la aceptación.

## Alcance

**Dentro (backend):**
- Avisos de partido: al árbitro asignado (creación y reasignación, incluido el que
  deja de pitarlo), y al árbitro + entrenadores de ambos equipos en reprogramación
  (fecha/cancha) y eliminación. **Deduplicando usuarios**: el mismo entrenador puede
  dirigir a los dos equipos del partido (así están los datos del seed y de los tests).
- Aviso "Torneo nuevo" a **todos** los entrenadores al crear un torneo (no hay
  concepto de audiencia: un torneo no pertenece a nadie hasta que hay inscripciones).
- Aviso "Inscripción aceptada" al entrenador dueño del equipo cuando la inscripción
  queda aceptada **y hoy nadie se lo dice**: (a) torneo sin cuota (aceptación directa,
  hoy silenciosa); (b) cuando la paga o confirma **otro** usuario (p. ej. el admin).
  Cuando el propio entrenador paga, el "Pago confirmado" existente ya es el aviso:
  duplicarlo sería ruido.
- Tests de cada trigger (filas de `Notificacion` por usuario, con deltas antes/después)
  y un test de encolado push del trigger principal, con el patrón de
  `test_push_integracion_*`.

**Dentro (móvil):**
- `Campanita` extraída a componente compartido (hoy vive dentro de `PlayerHomeScreen`)
  con el color como prop, y campana con punto de no-leídas en el inicio del coach
  (dorada) y en el del árbitro (blanca sobre guinda).
- `NotificationsScreen` registrada también como `NotificationsCoach` (cabecera dorada)
  y `NotificationsRef` (guinda). El componente es el mismo.
- Palabra clave "partido" en el mapa de iconos de la pantalla (los títulos nuevos).

**Fuera:**
- Flujo de rechazo de inscripciones (no existe; crear el mecanismo es otra feature).
- Notificaciones en el panel web (no consume `/notificaciones` y no se pidió).
- Deep-link del push a un evento concreto: el tap sigue abriendo la lista, y siempre
  la variante del jugador (`Notifications`, verde) — `push.js` no conoce el rol.
  Limitación anotada, no bloqueante: la lista es la misma.
- Preferencias/opt-out por usuario, columna `tipo`, agrupación: YAGNI.

## Decisiones

| Decisión | Elegido | Por qué |
|---|---|---|
| Dónde viven los triggers | En cada endpoint, llamando al servicio | Patrón existente (pagos, invitaciones). El helper local `_avisar_partido` solo añade la deduplicación de destinatarios. |
| Aceptación pagada por el propio coach | No se duplica el aviso | Ya recibe "Pago confirmado" con el concepto de la inscripción. Dos avisos por un acto es ruido. |
| Audiencia de "Torneo nuevo" | Todos los entrenadores | No hay suscripciones ni audiencia; es el único destinatario natural del evento. |
| Pantalla por rol | Tres registros del mismo componente | Cero lógica condicional de tema; mismo patrón que las demás pantallas por-rol del stack. |
| Viejo árbitro al reasignar | Recibe "Cambio de designación" | Es la otra mitad de "partido asignado": si no se le avisa, se presenta a pitar. |

## Verificación

- Tests nuevos en `api/tests/test_avisos.py` + el push de integración. La suite
  completa al final de la rama (los fixtures crean torneos y partidos por todos
  lados: cualquier aserción rota por los avisos nuevos tiene que salir ahí).
- `npm run verificar`.
- En dispositivo (usuario, por la mañana): crear un partido asignado al árbitro demo
  desde Swagger y ver llegar el aviso; campana con punto en ambos paneles; abrirla
  marca leído y el punto se apaga.
