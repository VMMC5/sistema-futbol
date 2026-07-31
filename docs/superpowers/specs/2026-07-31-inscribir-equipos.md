# Inscribir equipos a torneos desde la app del entrenador

Fecha: 2026-07-31
Estado: aprobado por el usuario (instrucción directa + decisiones de diseño), pendiente de plan

## Problema

El botón "Inscribir" del inicio del entrenador está `proximamente: true` desde la
primera entrega. El usuario pidió que el entrenador pueda inscribir sus equipos a los
torneos, respetando el cierre de inscripciones y la cuota (que lleva al módulo de
pagos cuando el torneo la exige).

## Hallazgo del reconocimiento: el backend ya está construido

`POST /inscripciones` (`api/app/routers/inscripciones.py:25-78`) ya valida todo:

- 403 si el equipo no es del entrenador; 400 si torneo/equipo no existen.
- 409 si el torneo está `finalizado`, si `fecha_cierre_inscripciones` ya pasó, si el
  equipo ya está inscrito (UNIQUE torneo+equipo) o si el cupo está lleno (solo cuentan
  `pendiente`+`aceptada`; una `rechazada` no ocupa lugar).
- **La cuota decide el estado inicial**: sin cuota (o cuota 0) la inscripción nace
  `aceptada`; con cuota nace `pendiente` y `POST /pagos/inscripcion/{id}`
  (`pagos.py:35-49`) la voltea a `aceptada` al completarse el pago — tarjeta al
  momento, o transferencia cuando el admin la confirma. Es el mismo patrón de las
  reservas, con sus mismos guards (403 ajeno, 409 doble pago, 402 tarjeta rechazada).
- `GET /inscripciones` ya filtra: el entrenador solo ve las de sus equipos.
- `PagoScreen` del móvil **ya acepta `tipo: "inscripcion"`** (`PagoScreen.js:11,38`):
  el flujo de pago y comprobante no necesita ni una línea.

**Decisión "respetar lo que ya exista" aplicada:** no hay flujo de aprobación manual
del admin (ningún endpoint pone `rechazada`; el estado fluye por pago). No se inventa
uno. "Pagar para confirmar" es exactamente lo que el backend ya hace.

## Alcance

**Dentro:**
- Pantalla nueva `InscribirScreen` (coach): elegir equipo propio, ver torneos con su
  estado de inscripción (abierto/cerrado/ya inscrito/cupo), inscribir, y pagar la
  cuota cuando aplique reutilizando `Pago`/`Comprobante`.
- Sección "Mis inscripciones" en la misma pantalla, con estado y botón "Pagar" para
  las pendientes con cuota (reentrada al pago si quedó a medias).
- Botón "Inscribir" del inicio del coach cableado a la pantalla.
- Test de API que cubra el 409 por `fecha_cierre_inscripciones` vencida — la rama
  existe (`inscripciones.py:44-45`) pero **ningún test la ejercita hoy**.

**Fuera:**
- Cancelar/retirar una inscripción (no existe endpoint; decisión aparte).
- Flujo de rechazo del admin y página de inscripciones en el panel web (no existen;
  el estado `rechazada` es hoy inalcanzable por código y se queda así).
- Lock del cupo (count-then-insert TOCTOU): deuda conocida, junto al lock del doble
  pago. Anotada, no de esta rama.
- Filtro "inscripciones abiertas" en el servidor: el cliente lo calcula con los campos
  que `GET /torneos` ya devuelve (`fecha_cierre_inscripciones`, `cuota_inscripcion`,
  `cupo_maximo`, `estado`).

## Decisiones

| Decisión | Elegido | Por qué |
|---|---|---|
| Dónde vive la UI | Una sola pantalla `InscribirScreen` | Mismo patrón de `ReservarScreen`: flujo completo en una pantalla, sin wizard. |
| Qué torneos se muestran | Los no `finalizado`, marcando "cerrado" si la fecha pasó | El servidor es la barrera real (409); el cliente solo evita el viaje perdido. ⚠️ Comparar `fecha_cierre_inscripciones` como **cadena ISO `YYYY-MM-DD`** contra la fecha local del dispositivo (el mismo truco de `proximosDias()` en `ReservarScreen`), no con `new Date("YYYY-MM-DD")`, que se interpreta como medianoche UTC y corre el cierre un día según la zona horaria. |
| Pago | Navegar a `Pago {tipo: "inscripcion", id, resumen}` | La pantalla ya es genérica; el 402/409/403 ya los maneja. |
| Con cuota pero sin pagar | Aparece "pendiente" con botón "Pagar" | La inscripción ya quedó creada; lo que falta es el pago. Reentrable. |
| Backend | Sin cambios de código | Ya hace todo. Solo se añade el test del cierre por fecha. |

## Verificación

- `npm run verificar` (⚠️ nunca `npx babel`).
- Test nuevo: torneo con `fecha_cierre_inscripciones` de ayer → `POST /inscripciones`
  responde 409. Los 7 tests existentes de inscripciones y los 4 de pago de inscripción
  siguen en verde.
- En dispositivo (usuario, por la mañana): inscribir un equipo a torneo gratis
  (aceptada directa) y a torneo con cuota (pendiente → pagar → aceptada).
