# Reservas de cancha para el entrenador

Fecha: 2026-07-31
Estado: aprobado por el usuario (instrucción directa), pendiente de plan

## Problema

El inicio del entrenador tiene un botón "Reservar" desde la primera entrega, pero está
marcado `proximamente: true`: al tocarlo solo sale un aviso. El jugador sí puede
reservar canchas desde su pestaña. El usuario pidió darle la misma capacidad al
entrenador usando ese botón que ya existe.

## Hallazgo del reconocimiento: no hay nada que abrir en el backend

- Los endpoints del flujo (`POST/GET /reservas`, `POST /reservas/{id}/cancelar`,
  `POST /pagos/reserva/{id}`, `GET /pagos/{id}`, `GET /pagos/{id}/recibo.pdf`,
  `GET /sedes`, `GET /canchas`, `GET /canchas/{id}/disponibilidad`) usan
  `get_current_user` sin guard de rol. El docstring de `reservas.py:9-12` lo declara a
  propósito: "Crear / ver lo propio: cualquier usuario autenticado".
- Las tres pantallas del flujo (`ReservarScreen`, `PagoScreen`, `ComprobanteScreen`)
  no leen el rol: ni importan `useAuth` ni ramifican por usuario.

**La feature entera es cableado de navegación en el móvil**, más un test de regresión
que fije en la suite que el entrenador puede reservar y pagar (hoy ningún test usa
`auth_entrenador` contra reservas/pagos: si alguien añadiera un `require_roles`
mañana, nada se pondría rojo).

## Alcance

**Dentro:**
- El botón "Reservar" del inicio del entrenador navega al flujo real de reserva.
- `ReservarScreen` registrada en el stack del entrenador con su cabecera dorada.
- Tests de API que fijen que el rol `entrenador` puede crear reserva y pagarla.

**Fuera:**
- Cambios de comportamiento en `ReservarScreen` (es agnóstica al rol; se monta tal cual).
- La cabecera de `Pago`/`Comprobante` seguirá verde (tema del jugador): son pantallas
  compartidas a nivel raíz y ya las usa el flujo de inscripción; cambiarles el tema por
  rol es otra tarea.
- El botón "Inscribir" del mismo menú (spec aparte, misma tanda nocturna).

## Decisiones

| Decisión | Elegido | Por qué |
|---|---|---|
| Cómo se monta para el coach | `Stack.Screen` raíz `ReservarCancha` | El jugador la tiene como pestaña `Reservar` dentro de su `Tab.Navigator`. Registrarla también como pantalla de stack con OTRO nombre evita el warning de React Navigation por nombres duplicados en navegadores anidados, y el patrón ya existe: `LineupMatches`, `TeamEdit`, etc. son stack screens del coach a las que `ACCIONES` navega por nombre. |
| Backend | Sin cambios | Ya lo permite. Solo se añaden tests que lo fijen. |
| Tests nuevos | En verde desde el primer run | No son TDD de código nuevo: son clavijas de regresión sobre comportamiento existente. |

## Verificación

- `npm run verificar` en `mobile/` (⚠️ nunca `npx babel`).
- Tests: entrenador crea reserva (201) y la paga con tarjeta (201, reserva `confirmada`).
- En dispositivo (usuario, por la mañana): entrar como `entrenador@demo.com`, tocar
  "Reservar", completar una reserva y pagarla.
