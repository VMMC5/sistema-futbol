# Reservas para el entrenador — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el botón "Reservar" del inicio del entrenador abra el flujo real de reserva de canchas, el mismo que ya usa el jugador.

**Architecture:** El backend ya lo permite (los endpoints de reservas/pagos usan `get_current_user` sin guard de rol) y las pantallas son agnósticas al rol. Todo el cambio es cableado: registrar `ReservarScreen` como pantalla de stack del coach con el nombre `ReservarCancha` (para no duplicar el nombre `Reservar` de la pestaña del jugador) y darle `destino` al botón. Más dos tests de API que fijen el comportamiento.

**Tech Stack:** React Native / Expo SDK 51 (`mobile/`), pytest (`api/tests/`).

## Global Constraints

- **Cero cambios de backend en `api/app/`**: el flujo ya está permitido. Solo se añaden tests.
- **Los dos tests nuevos NO son TDD de código nuevo**: son clavijas de regresión sobre comportamiento existente y deben salir **en verde desde el primer run**. Si alguno falla, algo se entendió mal — parar y reportar, no "arreglar" el router.
- `ReservarScreen`, `PagoScreen` y `ComprobanteScreen` **no se tocan**.
- La pantalla nueva del stack se llama **`ReservarCancha`** (no `Reservar`): el jugador ya tiene una pestaña `Reservar` dentro de su `Tab.Navigator` y duplicar nombres entre navegadores anidados dispara un warning de React Navigation.
- Comandos: `cd mobile && npm run verificar` (⚠️ **nunca `npx babel`**); tests desde `api/` con `.venv/bin/pytest`, solo los archivos afectados (la suite completa tarda ~12-18 min y corre al final de la rama).
- ⚠️ `mobile/app.json` tiene un cambio local sin commitear que NO es de esta tarea. Nunca `git add -A` ni `git commit -a`.

---

### Task 1: Cablear el botón "Reservar" del coach

**Files:**
- Modify: `mobile/src/screens/coach/CoachHomeScreen.js:15`
- Modify: `mobile/App.js:207` (bloque del panel del entrenador)

**Interfaces:**
- Consumes: `ReservarScreen` (ya importada en `App.js:34`), `goldHeader` (`App.js:107-112`).
- Produces: ruta de stack `ReservarCancha` que el botón navega por nombre.

- [ ] **Step 1: Dar destino al botón**

En `mobile/src/screens/coach/CoachHomeScreen.js`, cambiar la línea 15:

```js
  { icono: "calendar", label: "Reservar", proximamente: true },
```

por:

```js
  { icono: "calendar", label: "Reservar", destino: "ReservarCancha" },
```

(El handler `tocar()` de las líneas 39-45 ya navega cuando hay `destino`; no se toca. La entrada "Inscribir" de la línea 13 se queda `proximamente`: es otra feature.)

- [ ] **Step 2: Registrar la pantalla en el stack del coach**

En `mobile/App.js`, dentro del bloque `{/* Panel del entrenador (tema claro, cabecera dorada) */}`, justo después de la línea de `InvitePlayers` (hoy 207), insertar:

```jsx
          <Stack.Screen name="ReservarCancha" component={ReservarScreen} options={{ ...goldHeader, title: "RESERVAR CANCHA" }} />
```

No hace falta import nuevo: `ReservarScreen` ya se importa en la línea 34 para la pestaña del jugador.

- [ ] **Step 3: Verificar sintaxis**

Run: `cd mobile && npm run verificar`
Expected: sin errores. ⚠️ No usar `npx babel` (resuelve a babel v6 roto del caché).

- [ ] **Step 4: Comprobar que no quedó nombre duplicado**

Run: `cd mobile && grep -n 'name="Reservar' App.js`
Expected: exactamente 2 líneas — la pestaña `Reservar` del jugador (dentro de `PlayerTabs`) y el stack `ReservarCancha` nuevo. Ningún otro.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/screens/coach/CoachHomeScreen.js mobile/App.js
git commit -m "feat(movil): el boton Reservar del entrenador abre el flujo real de reserva"
```

---

### Task 2: Clavijas de regresión — el entrenador reserva y paga

**Files:**
- Modify: `api/tests/test_reservas.py` (un test al final)
- Modify: `api/tests/test_pagos.py` (un test al final)

**Interfaces:**
- Consumes: fixture `auth_entrenador` de `api/tests/conftest.py:131-134` (usuario `entrenador@demo.com` sembrado, dueño de los equipos 1 y 2); constantes `RESERVA_BASE` y `TARJETA_OK` ya definidas en cada archivo.
- Produces: nada. Son los últimos tests de la rama.

- [ ] **Step 1: Test en `test_reservas.py`**

Al final del archivo:

```python
def test_entrenador_tambien_reserva(client, auth_entrenador):
    """El flujo de reservas no es exclusivo del jugador: cualquier autenticado
    crea y ve las suyas (docstring del router). Clavija de regresión: si mañana
    alguien añade un require_roles al router, esto se pone rojo."""
    r = client.post("/reservas", headers=auth_entrenador, json=RESERVA_BASE)
    assert r.status_code == 201
    mias = client.get("/reservas", headers=auth_entrenador).json()
    assert any(x["id"] == r.json()["id"] for x in mias)
```

- [ ] **Step 2: Test en `test_pagos.py`**

Al final del archivo:

```python
def test_entrenador_paga_su_reserva(client, auth_entrenador):
    """La reserva del entrenador se paga y confirma igual que la del jugador."""
    rid = client.post("/reservas", headers=auth_entrenador, json=RESERVA_BASE).json()["id"]
    r = client.post(f"/pagos/reserva/{rid}", headers=auth_entrenador,
                    json={"metodo": "tarjeta", "tarjeta": TARJETA_OK})
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "completado"
    assert client.get(f"/reservas/{rid}", headers=auth_entrenador).json()["estado"] == "confirmada"
```

- [ ] **Step 3: Correrlos**

Run: `cd api && .venv/bin/pytest tests/test_reservas.py tests/test_pagos.py -v`
Expected: **todo PASSED al primer intento**, incluidos los dos nuevos. Si alguno de los dos nuevos falla, NO tocar `api/app/`: parar y reportar BLOCKED con la salida.

- [ ] **Step 4: Commit**

```bash
git add api/tests/test_reservas.py api/tests/test_pagos.py
git commit -m "test(api): fijar que el rol entrenador puede reservar y pagar"
```

---

## Verificación final

- [ ] `cd mobile && npm run verificar` sin errores.
- [ ] `cd api && .venv/bin/pytest tests/test_reservas.py tests/test_pagos.py -q` → 0 failed.
- [ ] En dispositivo (usuario, por la mañana): como `entrenador@demo.com`, tocar "Reservar" en el inicio, completar reserva y pago; la cabecera de la pantalla de reserva debe salir dorada.

## Qué queda fuera, a propósito

- Tema de cabecera de `Pago`/`Comprobante` (verde, compartidas con jugador).
- El botón "Inscribir" (spec y plan propios, misma tanda).
