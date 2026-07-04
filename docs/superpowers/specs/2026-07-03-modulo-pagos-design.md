# Diseño — Módulo de Pagos (IF-10)

**Fecha:** 2026-07-03
**Requisito:** IF-10 Pagos en línea (tarjeta de crédito/débito o transferencia bancaria; resumen del pago, datos necesarios y comprobante digital).
**Estado:** Aprobado — listo para plan de implementación.

## 1. Objetivo y alcance

Implementar el pago en línea de **reservas de cancha** y de **cuotas de inscripción de equipos a torneos**, con una **pasarela simulada (mock)** que cumpla el flujo completo de IF-10 sin cobrar dinero real. Incluye:

- Métodos: **tarjeta** (aprobación instantánea) y **transferencia** (queda pendiente hasta que el superadmin la confirma).
- **Comprobante digital**: detalle del pago en la app + **PDF descargable**.
- Cierre del hueco de **inscripciones de equipo a torneo** (hoy inexistente), necesario para pagar la cuota.

**Fuera de alcance:** integración con pasarela real (Stripe u otra). Se deja una costura (`PaymentGateway`) para enchufarla después sin tocar routers ni servicio.

## 2. Arquitectura (Opción A: router + servicio + gateway)

```
api/app/
├── gateway.py              # PaymentGateway (interfaz) + MockGateway
├── pagos_service.py        # orquestación: calcular monto, cobrar, confirmar, notificar
├── recibo_pdf.py           # genera el PDF del comprobante (fpdf2)
├── routers/
│   ├── pagos.py            # endpoints /pagos (HTTP + auth, delgado)
│   └── inscripciones.py    # inscripción de equipo a torneo
```

- El **router** solo hace HTTP + autorización; delega la lógica de dinero a `pagos_service`.
- `pagos_service` calcula el monto en el servidor, invoca el `gateway`, aplica los efectos (estado del pago, confirmación de reserva/inscripción, notificación) dentro de una transacción.
- `gateway.py` define `PaymentGateway` (interfaz) e implementa `MockGateway`. Sustituir por `StripeGateway` en el futuro = nueva clase.

### Interfaz del gateway

```
ResultadoCobro = { aprobado: bool, estado: str, referencia: str, motivo: str | None }

class PaymentGateway:
    def charge(self, monto: Decimal, metodo: str, datos_tarjeta: dict | None) -> ResultadoCobro: ...
```

## 3. Modelo de datos

Se reutiliza el modelo `Pago` existente (`usuario_id`, `monto`, `metodo`, `estado`, `referencia`, `creado_en`; 1:1 con `Reserva.pago_id` e `Inscripcion.pago_id`). **Migración Alembic** que agrega:

- `concepto` (String(160)) — snapshot legible para recibo/historial (ej. *"Reserva Cancha 1 · 2026-07-10 18:00"*).
- `completado_en` (DateTime(timezone=True), nullable) — cuándo se aprobó.

**Seguridad de datos:** no se persisten PAN/CVV. Tras el cobro se descartan; solo se guardan los **últimos 4 dígitos** dentro de `referencia`/`concepto`.

Estados de `Pago`: `pendiente` → `completado` | `fallido`.

## 4. API

### Inscripciones (nuevo)

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/inscripciones` | entrenador (su equipo) | Crea `Inscripcion` `pendiente`. Valida: torneo existe; inscripciones abiertas (estado del torneo y `fecha_cierre_inscripciones`); equipo pertenece al entrenador; no duplicada (`uq_inscripcion_torneo_equipo`); cupo (`cupo_maximo`) disponible. |
| GET | `/inscripciones` | entrenador / admin | Lista propias / todas; filtro `torneo_id`. |

### Pagos

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/pagos/reserva/{reserva_id}` | dueño de la reserva | Paga la reserva. Monto = `precio_hora × horas` (**calculado en el servidor**). |
| POST | `/pagos/inscripcion/{inscripcion_id}` | entrenador dueño del equipo | Paga la cuota. Monto = `torneo.cuota_inscripcion` (servidor). |
| GET | `/pagos` | usuario / admin | Historial (propio / todos). |
| GET | `/pagos/{id}` | dueño / admin | Detalle = comprobante en app. |
| GET | `/pagos/{id}/recibo.pdf` | dueño / admin | PDF (solo si `completado`). |
| POST | `/pagos/{id}/confirmar` | superadmin | Confirma una **transferencia** pendiente. |

**Regla de seguridad clave:** el cliente **nunca** envía el monto; siempre se calcula en el servidor a partir de la cancha/torneo. Si el cliente lo envía, se ignora.

### Esquemas Pydantic (nuevos)

- `PagoCreate` — `metodo: "tarjeta"|"transferencia"`; si tarjeta: `numero`, `exp_mes`, `exp_anio`, `cvv`, `titular` (validados, no persistidos).
- `PagoOut` — `id`, `concepto`, `monto`, `metodo`, `estado`, `referencia`, `creado_en`, `completado_en`, `usuario_nombre`.
- `InscripcionCreate` — `torneo_id`, `equipo_id`.
- `InscripcionOut` — `id`, `torneo_id`, `torneo_nombre`, `equipo_id`, `equipo_nombre`, `estado`, `pago_id`.

## 5. Flujos

### Tarjeta (síncrono)

1. Verifica propiedad y que no esté ya pagada (guard idempotencia → 409).
2. Calcula el monto en el servidor.
3. `gateway.charge(monto, "tarjeta", datos)`.
4. **Aprobado** → `Pago(estado="completado", completado_en=now, referencia="MOCK-xxxx·últimos4")`; `reserva.estado="confirmada"` (inscripción → `"aceptada"`); crea `Notificacion` "Pago confirmado…".
5. **Rechazado** → `Pago(estado="fallido")` → HTTP 402; la reserva/inscripción sigue `pendiente` (reintentable).

### Transferencia (asíncrono)

1. `POST /pagos/...` con `metodo="transferencia"` → `Pago(estado="pendiente", referencia="TRF-xxxx")`; reserva/inscripción siguen `pendiente`; notifica "pendiente de confirmación".
2. `POST /pagos/{id}/confirmar` (superadmin) → `Pago` `completado` + confirma reserva/inscripción + notifica al usuario.

## 6. MockGateway — reglas

- **tarjeta:** valida formato (número 13–19 dígitos, expiración futura, CVV 3 dígitos). Regla de rechazo **determinista** para demo/tests: número que **termina en `0000` → rechazada** ("fondos insuficientes"); cualquier otra → aprobada. Referencia `MOCK-<8hex>`.
- **transferencia:** siempre `pendiente`, referencia `TRF-<8hex>`.

## 7. Cálculo del monto (servidor)

- **Reserva:** `precio_hora × horas`, con `horas = hora_fin − hora_inicio`, redondeado a 2 decimales.
- **Inscripción:** `torneo.cuota_inscripcion`.
- **Edge (inscripción gratuita):** si la cuota es `0`/`None`, la inscripción se acepta directo sin crear pago; el POST de pago responde 400 "no requiere pago".

## 8. Comprobante

- `GET /pagos/{id}` → `PagoOut` con folio (`referencia`), concepto, monto, método, estado, fecha, nombre del usuario y detalle del concepto.
- `GET /pagos/{id}/recibo.pdf` → `fpdf2` genera un recibo simple (encabezado del sistema, folio, concepto, monto, método, estado, fecha, titular). Solo si `estado="completado"`; si no → 409. Se devuelve como `application/pdf`.

## 9. Clientes

### Móvil (Expo)

- `PagoScreen` reutilizable (recibe `concepto` + `id`): muestra resumen (concepto y monto del servidor), selector tarjeta/transferencia, formulario de tarjeta, botón pagar.
- `ComprobanteScreen`: comprobante + botón "Descargar PDF" (descarga autenticada con `expo-file-system`, compartir con `expo-sharing`).
- Cableado: `ReservarScreen` → tras crear la reserva navega a `PagoScreen`; detalle de torneo → "Inscribir equipo" → crea inscripción → `PagoScreen`. Historial de pagos en el perfil (IF-03).

### Web admin (Flask)

- Página **"Pagos"** que lista transferencias `pendiente` con botón **Confirmar** (`POST /pagos/{id}/confirmar`). Da soporte al método asíncrono.

## 10. Manejo de errores

| Código | Caso |
|---|---|
| 400 | Datos de tarjeta inválidos; concepto sin costo (inscripción gratuita) |
| 402 | Tarjeta rechazada por el gateway |
| 403 | Pagar/ver algo ajeno |
| 404 | Reserva/inscripción/pago inexistente |
| 409 | Ya pagada; PDF de pago no completado; confirmar algo que no es transferencia pendiente |
| 422 | Validación Pydantic |

## 11. Pruebas (pytest)

- **Unit `MockGateway`:** aprueba; rechaza (termina en `0000`); transferencia pendiente.
- **API:**
  - Tarjeta OK → reserva confirmada + pago completado + notificación.
  - Tarjeta rechazada → pago fallido + reserva sigue pendiente.
  - Pagar reserva ajena → 403.
  - Doble pago → 409.
  - Transferencia → pendiente → admin confirma → completado.
  - Inscripción: crear + pagar (feliz) + validaciones (cupo, duplicada, equipo ajeno).
  - **El monto lo fija el servidor** (si el cliente manda otro, se ignora).
  - Inscripción gratuita (cuota 0/None).
  - PDF solo si `completado` (si no, 409).

## 12. Dependencias nuevas

- `fpdf2` en `api/requirements.txt` (generación del PDF del recibo).
- Móvil: `expo-file-system`, `expo-sharing` (descarga/compartir del PDF autenticado).

## 13. Trazabilidad con requerimientos

- **IF-10** — cubierto: tarjeta + transferencia, resumen del pago, datos necesarios, comprobante en app + PDF.
- **IF-09** — completa el flujo de reserva con "confirmación de pago".
- **IF-05/IF-06** — habilita la inscripción de equipo a torneo con pago de cuota.
- **RNF-02 (seguridad)** — monto calculado en servidor, sin persistir datos de tarjeta, autorización por propiedad, guard de idempotencia.
