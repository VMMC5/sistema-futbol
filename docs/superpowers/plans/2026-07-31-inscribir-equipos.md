# Inscribir equipos a torneos — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el entrenador inscriba sus equipos a torneos desde la app, pagando la cuota cuando el torneo la exige.

**Architecture:** El backend ya hace todo (`POST /inscripciones` valida propiedad/cierre/duplicado/cupo y decide el estado por la cuota; `POST /pagos/inscripcion/{id}` completa el pago; `PagoScreen` ya acepta `tipo: "inscripcion"`). Se construye una sola pantalla nueva, `InscribirScreen`, al estilo de `ReservarScreen` (flujo completo en una pantalla), se cablea el botón que ya existe y se añade el único test de API que falta (cierre por fecha).

**Tech Stack:** React Native / Expo SDK 51 (`mobile/`), pytest (`api/tests/`).

## Global Constraints

- **Cero cambios en `api/app/`**: el backend ya implementa el flujo completo. Solo se añade un test.
- El test nuevo es una **clavija de regresión** sobre la rama de `inscripciones.py:44-45` que ya existe: debe salir **verde al primer run**. Si falla, parar y reportar BLOCKED — no tocar el router.
- **El cliente no recalcula reglas de negocio**: pinta estados con los campos que el servidor da y deja que el 409 del servidor sea la barrera. El cálculo de "cerrado" en la pantalla es solo para evitar un viaje perdido.
- `PagoScreen` y `ComprobanteScreen` **no se tocan** (ya son genéricas).
- Textos y comentarios en español, como el resto de la app.
- Comandos: `cd mobile && npm run verificar` (⚠️ **nunca `npx babel`**); tests desde `api/` con `.venv/bin/pytest tests/test_inscripciones.py`.
- ⚠️ `mobile/app.json` tiene un cambio local que NO es de esta rama. Nunca `git add -A` ni `git commit -a`.
- Esta rama sale de `feat/reservas-entrenador` (la feature A toca las mismas dos zonas de `App.js` y `CoachHomeScreen.js`; encadenarlas evita conflictos). Los números de línea de abajo son de después de la feature A.

---

### Task 1: Test del cierre de inscripciones por fecha

**Files:**
- Modify: `api/tests/test_inscripciones.py` (un test al final)

**Interfaces:**
- Consumes: helper `_torneo(client, auth_admin, **over)` ya definido en el archivo (línea 4), fixtures `auth_admin`/`auth_entrenador`.
- Produces: nada.

- [ ] **Step 1: Escribir el test**

Al final de `api/tests/test_inscripciones.py`:

```python
def test_no_inscribe_tras_el_cierre(client, auth_admin, auth_entrenador):
    """La rama del 409 por fecha_cierre_inscripciones vencida existe desde el
    principio (inscripciones.py) pero ningún test la ejercitaba. El día del
    cierre todavía se puede inscribir; a partir del siguiente, no."""
    tid = _torneo(client, auth_admin, fecha_cierre_inscripciones="2020-01-01")
    r = client.post("/inscripciones", headers=auth_entrenador, json={"torneo_id": tid, "equipo_id": 1})
    assert r.status_code == 409
```

- [ ] **Step 2: Correrlo**

Run: `cd api && .venv/bin/pytest tests/test_inscripciones.py -v`
Expected: **8 PASSED al primer intento** (7 existentes + este). Si el nuevo falla, NO tocar `api/app/`: reportar BLOCKED con la salida.

- [ ] **Step 3: Commit**

```bash
git add api/tests/test_inscripciones.py
git commit -m "test(api): cubrir el 409 por cierre de inscripciones vencido"
```

---

### Task 2: `InscribirScreen` y cableado del botón

**Files:**
- Create: `mobile/src/screens/coach/InscribirScreen.js`
- Modify: `mobile/src/screens/coach/CoachHomeScreen.js:13` (la entrada "Inscribir" de `ACCIONES`)
- Modify: `mobile/App.js` (import + registro en el bloque del entrenador)

**Interfaces:**
- Consumes: `GET /equipos` (equipos del entrenador: `{id, nombre, ...}`), `GET /torneos` (autenticado; cada torneo trae `id, nombre, estado, fecha_cierre_inscripciones, cuota_inscripcion, cupo_maximo`), `GET /inscripciones` (solo las de sus equipos: `{id, torneo_id, torneo_nombre, equipo_id, equipo_nombre, estado, pago_id}`), `POST /inscripciones {torneo_id, equipo_id}` → `InscripcionOut`; pantalla `Pago` con params `{tipo: "inscripcion", id, resumen}`.
- Produces: ruta de stack `Inscribir` a la que navega el botón del inicio.

- [ ] **Step 1: Crear la pantalla**

Crear `mobile/src/screens/coach/InscribirScreen.js`:

```jsx
// Inscripción de equipos a torneos: el entrenador elige uno de sus equipos, ve
// qué torneos admiten inscripción y paga la cuota cuando el torneo la exige.
// El servidor es la barrera real (409 por cierre/duplicado/cupo); esta pantalla
// solo pinta estados y evita viajes perdidos, no recalcula reglas.
import React, { useCallback, useMemo, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { lp, ls } from "../../publicTheme";

// Fecha local del dispositivo como cadena ISO (mismo truco de proximosDias()
// en ReservarScreen): new Date("YYYY-MM-DD") se interpreta como medianoche UTC
// y correría el cierre un día según la zona horaria.
function hoyISO() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// El día del cierre todavía se puede inscribir (el servidor rechaza con >);
// cerrado es a partir del día siguiente. Ante cualquier duda, manda el servidor.
function yaCerro(t) {
  return !!t.fecha_cierre_inscripciones && t.fecha_cierre_inscripciones < hoyISO();
}

function Etiqueta({ texto, fondo, color }) {
  return (
    <View style={{ backgroundColor: fondo, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 }}>
      <Text style={{ color, fontSize: 11, fontWeight: "800" }}>{texto}</Text>
    </View>
  );
}

export default function InscribirScreen({ navigation }) {
  const [equipos, setEquipos] = useState([]);
  const [torneos, setTorneos] = useState([]);
  const [inscripciones, setInscripciones] = useState([]);
  const [equipoSel, setEquipoSel] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [eqs, tns, ins] = await Promise.all([
        apiGet("/equipos"), apiGet("/torneos"), apiGet("/inscripciones"),
      ]);
      setEquipos(eqs);
      setTorneos(tns.filter((t) => t.estado !== "finalizado"));
      setInscripciones(ins);
      setEquipoSel((prev) => prev ?? (eqs.length ? eqs[0].id : null));
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar");
    } finally {
      setCargando(false);
    }
  }, []);

  // Recarga al volver del pago: la inscripción pendiente ya aparece aceptada.
  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  // Inscripciones del equipo elegido, indexadas por torneo
  const delEquipo = useMemo(() => {
    const mapa = {};
    for (const i of inscripciones) if (i.equipo_id === equipoSel) mapa[i.torneo_id] = i;
    return mapa;
  }, [inscripciones, equipoSel]);

  const equipo = equipos.find((e) => e.id === equipoSel);

  async function inscribir(t) {
    setEnviando(true);
    try {
      const ins = await apiPost("/inscripciones", { torneo_id: t.id, equipo_id: equipoSel });
      if (ins.estado === "aceptada") {
        // Torneo sin cuota: el servidor la acepta directamente.
        Alert.alert("Inscripción aceptada", `${equipo?.nombre} quedó inscrito en ${t.nombre}.`);
        cargar();
      } else {
        // Con cuota nace pendiente: se confirma al completar el pago.
        navigation.navigate("Pago", {
          tipo: "inscripcion", id: ins.id,
          resumen: `Inscripción: ${equipo?.nombre} — ${t.nombre}`,
        });
      }
    } catch (e) {
      Alert.alert("No se pudo inscribir", e.message || "Inténtalo de nuevo");
    } finally {
      setEnviando(false);
    }
  }

  function pagar(i) {
    navigation.navigate("Pago", {
      tipo: "inscripcion", id: i.id,
      resumen: `Inscripción: ${i.equipo_nombre || equipo?.nombre || ""} — ${i.torneo_nombre || ""}`,
    });
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }

  if (!equipos.length) {
    return (
      <View style={ls.screen}>
        <Text style={[ls.muted, { margin: 20 }]}>No tienes equipos registrados. Crea tu equipo antes de inscribirlo a un torneo.</Text>
      </View>
    );
  }

  const misInscripciones = inscripciones.filter((i) => i.equipo_id === equipoSel);

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Selector de equipo */}
      {equipos.length > 1 && (
        <View style={ls.tabs}>
          {equipos.map((e) => (
            <TouchableOpacity key={e.id} style={[ls.tab, equipoSel === e.id && { backgroundColor: lp.gold }]} onPress={() => setEquipoSel(e.id)}>
              <Text style={[ls.tabText, equipoSel === e.id && { color: lp.goldText, fontWeight: "800" }]}>{e.nombre}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <Text style={ls.sectionTitle}>Torneos disponibles</Text>
      {torneos.length === 0 && <Text style={ls.muted}>No hay torneos abiertos por ahora.</Text>}
      {torneos.map((t) => {
        const ins = delEquipo[t.id];
        const cerrado = yaCerro(t);
        return (
          <View key={t.id} style={ls.row}>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{t.nombre}</Text>
              <Text style={ls.muted}>
                {t.cuota_inscripcion > 0 ? `Cuota: $${t.cuota_inscripcion}` : "Sin cuota"}
                {t.fecha_cierre_inscripciones ? ` · Cierra: ${t.fecha_cierre_inscripciones}` : ""}
              </Text>
            </View>
            {ins?.estado === "aceptada" ? (
              <Etiqueta texto="INSCRITO" fondo={lp.green} color={lp.white} />
            ) : ins?.estado === "pendiente" ? (
              <TouchableOpacity onPress={() => pagar(ins)} disabled={enviando}>
                <Etiqueta texto="PAGAR CUOTA" fondo={lp.maroon} color={lp.white} />
              </TouchableOpacity>
            ) : cerrado ? (
              <Etiqueta texto="CERRADO" fondo={lp.surfaceBorder} color={lp.textMuted} />
            ) : (
              <TouchableOpacity onPress={() => inscribir(t)} disabled={enviando}>
                <Etiqueta texto="INSCRIBIR" fondo={lp.gold} color={lp.goldText} />
              </TouchableOpacity>
            )}
          </View>
        );
      })}

      <Text style={ls.sectionTitle}>Mis inscripciones{equipo ? ` · ${equipo.nombre}` : ""}</Text>
      {misInscripciones.length === 0 && <Text style={ls.muted}>Este equipo no tiene inscripciones.</Text>}
      {misInscripciones.map((i) => (
        <View key={i.id} style={ls.row}>
          <Text style={[ls.rowTitle, { flex: 1 }]}>{i.torneo_nombre || `Torneo ${i.torneo_id}`}</Text>
          {i.estado === "aceptada"
            ? <Etiqueta texto="ACEPTADA" fondo={lp.green} color={lp.white} />
            : <TouchableOpacity onPress={() => pagar(i)} disabled={enviando}>
                <Etiqueta texto="PENDIENTE · PAGAR" fondo={lp.maroon} color={lp.white} />
              </TouchableOpacity>}
        </View>
      ))}
    </ScrollView>
  );
}
```

- [ ] **Step 2: Cablear el botón del inicio**

En `mobile/src/screens/coach/CoachHomeScreen.js`, cambiar la línea de `ACCIONES`:

```js
  { icono: "docadd", label: "Inscribir", proximamente: true },
```

por:

```js
  { icono: "docadd", label: "Inscribir", destino: "Inscribir" },
```

- [ ] **Step 3: Registrar la pantalla**

En `mobile/App.js`:

1. Junto a los imports de pantallas del coach (cerca de `import TeamListScreen ...`), añadir:

```js
import InscribirScreen from "./src/screens/coach/InscribirScreen";
```

2. En el bloque `{/* Panel del entrenador ... */}`, junto a la línea de `ReservarCancha` (feature A), añadir:

```jsx
          <Stack.Screen name="Inscribir" component={InscribirScreen} options={{ ...goldHeader, title: "INSCRIBIR EQUIPO" }} />
```

- [ ] **Step 4: Verificar**

Run: `cd mobile && npm run verificar`
Expected: sin errores. ⚠️ No usar `npx babel`.

Run: `cd mobile && grep -rn "proximamente" src/screens/coach/CoachHomeScreen.js`
Expected: **cero líneas** — con esta feature y la A, ya no queda ningún botón muerto en el inicio del coach.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/screens/coach/InscribirScreen.js mobile/src/screens/coach/CoachHomeScreen.js mobile/App.js
git commit -m "feat(movil): el entrenador inscribe sus equipos a torneos y paga la cuota"
```

---

## Verificación final

- [ ] `cd api && .venv/bin/pytest tests/test_inscripciones.py tests/test_pagos_inscripcion.py -q` → 0 failed.
- [ ] `cd mobile && npm run verificar` sin errores.
- [ ] En dispositivo (usuario, por la mañana): inscribir un equipo a un torneo sin cuota (queda ACEPTADA al momento) y a uno con cuota (PAGAR CUOTA → pago con tarjeta → vuelve y aparece ACEPTADA).

## Qué queda fuera, a propósito

- Cancelar/retirar inscripciones (no hay endpoint; decisión aparte).
- Flujo de rechazo del admin y página de inscripciones en el panel web.
- Lock del cupo (TOCTOU count-then-insert), anotado junto al lock del doble pago.
- Filtro "abiertos" en el servidor: el cliente usa los campos que ya vienen.
