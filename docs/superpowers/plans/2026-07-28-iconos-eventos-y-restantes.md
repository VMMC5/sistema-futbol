# Iconos en eventos de partido y emojis restantes (móvil) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sustituir los 14 emojis de color que quedan en la app móvil y ampliar el verificador de nombres de icono para que cubra también los usos dinámicos.

**Architecture:** El catálogo pasa de 16 a 20 iconos, generados con el script existente; `Icono.js` no cambia. Cuatro pantallas son sustitución directa; dos (`RefLiveScreen`, `LineupPitch`) cambian el tipo de retorno de una función interna y son las únicas que pueden romper comportamiento.

**Tech Stack:** React Native 0.74.5 / Expo SDK 51, `react-native-svg` 15.2.0. Sin backend.

**Spec:** `docs/superpowers/specs/2026-07-28-iconos-eventos-y-restantes-design.md`

## Global Constraints

- **No se toca `api/` ni `web/`.** La suite de Python debe seguir en **233 en verde**. Tarda **~12,5 minutos**.
- **Verificación:** `cd mobile && npm run verificar <archivos…>`, `npm run verificar-iconos`, `npm run verificar-nombres`. **Prohibido `npx babel`**: resuelve al paquete `babel` v6 deprecado del caché de npx y hace fallar archivos válidos.
- **El paquete npm `reicon` nunca entra en `node_modules` ni en `package.json`.** Se descarga a `/tmp` y se descarta.
- **`Icono.js` NO se modifica.** Si algo parece exigirlo, para y reporta.
- **`iconos-datos.json` debe acabar con exactamente 20 claves.**
- **Los 8 caracteres tipográficos quedan fuera de alcance**, por decisión explícita del usuario: `✓` (`RefEventScreen:34`, `RefSummaryScreen:98`, `RefHistoryScreen:41`), `✕` (`NotificationsScreen:90`, `TeamEditScreen:117`), `↑ ↓` (`LineupPitch:22-23`), `→` (`LoginScreen:68`). **No los toques.**
- **Idioma:** comentarios, nombres y textos de UI en español.
- **Rama:** `feat/iconos-eventos-movil`, ya creada. El spec está commiteado en `99daa73`.
- **No hay runner de tests JS.** Nada cubre `mobile/`. Un defecto de ejecución solo lo detecta la validación en dispositivo.

### Dos temas distintos en esta app

`mobile/src/publicTheme.js` (`lp`, `ls`, `cs`) es el tema **claro** y lo usan casi todas las pantallas. `mobile/src/theme.js` (`colors`, `styles`) es el tema **oscuro** y solo lo usan las pantallas de cuenta/roles, entre ellas `HomeScreen` y `RegisterStaffScreen` de la Task 2. **Los colores de icono de esas dos salen de `colors`, no de `lp`.**

### Riesgo dominante de esta tanda

Las Tasks 4 y 5 cambian el **tipo de retorno** de `resumenEvento()` y `badgesDe()`. Es el primer trabajo de las tres tandas de iconos que puede romper comportamiento y no solo aspecto. Sus consumidores están en el mismo archivo, pero hay que actualizarlos en el mismo commit.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `mobile/scripts/generar-iconos.cjs` | **Modificar.** Cuatro iconos más; `tarjeta` se deriva del `<rect>`. |
| `mobile/scripts/verificar-nombres-iconos.cjs` | **Modificar.** Tres patrones en vez de uno. |
| `mobile/scripts/verificar-iconos.cjs` | **Modificar.** `ESPERADOS` de 16 a 20. |
| `mobile/src/components/iconos-datos.json` | **Modificar.** De 16 a 20. |
| `mobile/src/publicTheme.js` | **Modificar.** Añade `lp.amarilla`. |
| `mobile/src/screens/HomeScreen.js` | **Modificar.** `📨` → `envelope`. |
| `mobile/src/screens/RegisterStaffScreen.js` | **Modificar.** `📎` → `paperclip`. |
| `mobile/src/screens/player/NotificationsScreen.js` | **Modificar.** 3 de sus 5 ramas. |
| `mobile/src/screens/referee/RefSummaryScreen.js` | **Modificar.** Goles y tarjetas. |
| `mobile/src/screens/referee/RefLiveScreen.js` | **Modificar.** `resumenEvento()` devuelve objeto. |
| `mobile/src/components/LineupPitch.js` | **Modificar.** `badgesDe()` devuelve icono + veces. |
| `docs/superpowers/checklist-iconos-eventos.md` | **Crear.** Checklist de dispositivo. |

---

## Task 1: Catálogo a 20 iconos y verificador de nombres ampliado

**Files:**
- Modify: `mobile/scripts/generar-iconos.cjs`
- Modify: `mobile/scripts/verificar-iconos.cjs`
- Modify: `mobile/scripts/verificar-nombres-iconos.cjs`
- Modify: `mobile/src/components/iconos-datos.json`
- Modify: `mobile/src/publicTheme.js`

**Interfaces:**
- Produces: cuatro claves nuevas en `iconos-datos.json` — `transfer`, `tarjeta`, `envelope`, `paperclip`. Formato `{ d: string[], trazo?: true, parImpar?: true }`.
- Produces: `lp.amarilla` = `"#f2b53c"` en `publicTheme.js`.
- Produces: `npm run verificar-nombres` reconociendo tres formas: `<Icono nombre="…">`, `icono="…"` e `icono: "…"`.

- [ ] **Step 1: Descargar reicon a /tmp**

```bash
rm -rf /tmp/reicon-gen && mkdir -p /tmp/reicon-gen && cd /tmp/reicon-gen && \
  npm pack reicon@1.1.103 >/dev/null 2>&1 && tar xzf reicon-*.tgz && \
  ls package/icons/Envelope.js package/icons/Paperclip.js
```

Esperado: las dos rutas sin error. **No instales `reicon` en el proyecto.**

- [ ] **Step 2: Ampliar el generador**

En `mobile/scripts/generar-iconos.cjs`, añade `"transfer"` al final de `DESDE_WEB`:

```js
const DESDE_WEB = ["cuptrophy", "chart", "calendar", "people", "football", "transfer"];
```

Añade dos entradas a `DESDE_REICON`:

```js
  envelope: "Envelope",
  paperclip: "Paperclip",
```

Y **antes** de la línea `const macro = fs.readFileSync(...)`, añade el mapa de literales:

```js
// Iconos cuyo dato NO se puede extraer de la fuente porque no es un <path>.
// El "tarjeta" del macro web es <rect x="6" y="2.5" width="12" height="19" rx="2.2"/>.
// A diferencia de "location" (que mezcla circle/line/g y por eso se tomó de reicon),
// un rectangulo redondeado se expresa EXACTAMENTE como path, sin perdida:
// esquinas (6,2.5)-(18,21.5) y radio 2.2 en las cuatro.
const LITERALES = {
  tarjeta: {
    d: ["M8.2 2.5 H15.8 A2.2 2.2 0 0 1 18 4.7 V19.3 A2.2 2.2 0 0 1 15.8 21.5 H8.2 A2.2 2.2 0 0 1 6 19.3 V4.7 A2.2 2.2 0 0 1 8.2 2.5 Z"],
  },
};
```

Y justo antes del `console.log(JSON.stringify(...))` final:

```js
Object.assign(salida, LITERALES);
```

- [ ] **Step 3: Generar y comprobar los recuentos**

```bash
cd mobile
node scripts/generar-iconos.cjs /tmp/reicon-gen/package > /tmp/iconos-v3.json
node -e '
const d = require("/tmp/iconos-v3.json");
const ESPERADO = { cuptrophy:[2,false], chart:[1,false], calendar:[7,false], people:[6,true],
  football:[1,false], transfer:[2,false], home:[2,false], user:[2,false], history:[1,false],
  clipboardlist:[1,false], docadd:[1,false], location:[1,false],
  envelope:[1,false], paperclip:[1,false], tarjeta:[1,false] };
let malos = 0;
for (const [k,[n,trazo]] of Object.entries(ESPERADO)) {
  const e = d[k];
  if (!e || e.d.length !== n || !!e.trazo !== trazo) {
    console.log(`FALLO ${k}: paths=${e && e.d.length} (esperado ${n}), trazo=${e && !!e.trazo} (esperado ${trazo})`); malos++;
  }
}
console.log(malos ? `${malos} discrepancias` : `OK: ${Object.keys(ESPERADO).length} iconos con los paths esperados`);
process.exit(malos ? 1 : 0);'
```

Esperado: `OK: 15 iconos con los paths esperados`. Si algún recuento no cuadra, **para y reporta**: la fuente cambió.

- [ ] **Step 4: Fusionar en iconos-datos.json**

```bash
cd mobile
node -e '
const fs = require("fs");
const viejos = require("./src/components/iconos-datos.json");
const nuevos = require("/tmp/iconos-v3.json");
const todos = { ...viejos, ...nuevos };
fs.writeFileSync("./src/components/iconos-datos.json", JSON.stringify(todos, null, 2) + "\n");
console.log("total de iconos: " + Object.keys(todos).length);'
```

Esperado: `total de iconos: 20`. El generador reemite también los 11 anteriores; al fusionar con `...nuevos` último, quedan idénticos (son deterministas) y entran los 4 nuevos.

- [ ] **Step 5: Ampliar `verificar-iconos.cjs` a 20 claves**

Sustituye su lista `ESPERADOS` por:

```js
const ESPERADOS = [
  "edit", "creditcard", "lock", "logout", "bell",
  "cuptrophy", "chart", "calendar", "people", "football",
  "home", "user", "history", "clipboardlist", "docadd", "location",
  "transfer", "tarjeta", "envelope", "paperclip",
];
```

No toques el resto del script.

- [ ] **Step 6: Añadir el amarillo a la paleta**

En `mobile/src/publicTheme.js`, dentro del objeto `lp`, junto a `danger` y `red`, añade **dos** entradas:

```js
  amarilla: "#f2b53c",    // tarjeta amarilla; mismo valor que .ic-amarilla de la web
  rojaClara: "#ff5a5a",   // tarjeta roja SOBRE FONDO OSCURO (la cancha, #1C6B3A)
```

**Por qué dos rojos.** El mismo icono de tarjeta aparece sobre dos fondos muy
distintos: el claro de las listas del árbitro (`lp.bg`, `#EDEAE1`) y el **verde
oscuro de la cancha** (`#1C6B3A`, en `LineupPitch`). El `lp.danger` que ya existe
(`#c0392b`) contrasta bien sobre claro y mal sobre el verde. `rojaClara` es el
mismo `--danger` que el panel web usa sobre su fondo oscuro. Reparto:

| Dónde | Fondo | Amarilla | Roja |
|---|---|---|---|
| `RefSummaryScreen`, `RefLiveScreen` | claro | `lp.amarilla` | `lp.danger` |
| `LineupPitch` (cancha) | verde oscuro | `lp.amarilla` | `lp.rojaClara` |

- [ ] **Step 7: Ampliar el verificador de nombres**

Sustituye el bloque de comentario de cabecera **y** el bucle de detección de `mobile/scripts/verificar-nombres-iconos.cjs`. La cabecera pasa a:

```js
// Comprueba que todo nombre de icono usado exista en iconos-datos.json.
// Una errata no lanza error en ejecucion: pinta un hueco vacio. Esto lo caza.
// Uso: node scripts/verificar-nombres-iconos.cjs   (o npm run verificar-nombres)
//
// Reconoce tres formas, que juntas cubren todos los usos literales del proyecto:
//   <Icono nombre="football">      render directo
//   <OpcionMenu icono="edit">      prop que otro componente pasa a <Icono>
//   { icono: "people", ... }       clave de objeto (ACCIONES, ICONO de eventos)
// La primera va acotada a <Icono> a proposito: <Avatar> tiene una prop `nombre`
// que no es un icono, y sin acotar daria falsos positivos.
//
// Limite que PERMANECE: un valor calculado en tiempo de ejecucion sigue siendo
// invisible. Esto cubre lo literal, que es todo lo que el proyecto usa hoy.
```

Y el bucle de detección pasa de un `matchAll` a tres:

```js
const PATRONES = [
  [/<Icono\b[^>]*?\snombre="([a-z0-9]+)"/g, 'nombre='],
  [/\sicono="([a-z0-9]+)"/g, 'icono='],
  [/\bicono:\s*"([a-z0-9]+)"/g, 'icono:'],
];

let malos = 0;
let vistos = 0;
for (const archivo of archivos) {
  const txt = fs.readFileSync(archivo, "utf8");
  for (const [patron, etiqueta] of PATRONES) {
    for (const m of txt.matchAll(patron)) {
      vistos++;
      if (!iconos.has(m[1])) {
        console.log(`FALLO ${path.relative(RAIZ, archivo)}: ${etiqueta}"${m[1]}" no existe en iconos-datos.json`);
        malos++;
      }
    }
  }
}
console.log(malos ? `${malos} nombres inválidos` : `OK: ${vistos} usos de icono, todos existen`);
process.exit(malos ? 1 : 0);
```

- [ ] **Step 8: Comprobar que el verificador detecta erratas en las TRES formas**

Sin esto no sabes si la ampliación sirve. Cada bloque debe dar `exit=1`:

**Los nombres de prueba NO deben llevar dígitos.** Las regex usan `[a-z0-9]+`, pero
si escribes `noexiste1` y el patrón fuera `[a-z]+`, no habría coincidencia y la
prueba pasaría en verde sin probar nada. Usa nombres solo de letras:

```bash
cd mobile
for caso in 'export const A = <Icono nombre="noexiste" />;' \
            'export const B = <OpcionMenu icono="tampoco" />;' \
            'export const C = { icono: "inventado" };'; do
  echo "$caso" > src/_prueba.js
  npm run verificar-nombres --silent >/dev/null 2>&1; echo "$caso -> exit=$?"
  rm -f src/_prueba.js
done
npm run verificar-nombres
```

Esperado: los tres casos con `exit=1`, y la última línea `OK: 30 usos de icono, todos existen`. Si algún caso sale 0, **para**: ese patrón no está funcionando.

Comprueba también que **no hay falso positivo con `Avatar`**:

```bash
cd mobile
printf 'export const D = <Avatar nombre="juan" />;\n' > src/_prueba.js
npm run verificar-nombres --silent; echo "exit=$? (debe ser 0)"
rm -f src/_prueba.js
```

- [ ] **Step 9: Verificar sintaxis y commitear**

```bash
cd mobile && npm run verificar -- scripts/generar-iconos.cjs scripts/verificar-nombres-iconos.cjs scripts/verificar-iconos.cjs src/publicTheme.js
cd .. && git add mobile/scripts/generar-iconos.cjs mobile/scripts/verificar-iconos.cjs \
  mobile/scripts/verificar-nombres-iconos.cjs mobile/src/components/iconos-datos.json mobile/src/publicTheme.js
git commit -m "feat(movil): catalogo a 20 iconos y verificador de nombres ampliado"
```

---

## Task 2: Pantallas de sustitución directa

**Files:**
- Modify: `mobile/src/screens/HomeScreen.js:55`
- Modify: `mobile/src/screens/RegisterStaffScreen.js:112-116`
- Modify: `mobile/src/screens/player/NotificationsScreen.js:9-16,83`

**Interfaces:**
- Consumes: `envelope`, `paperclip`, `football`, `cuptrophy`, `bell` del catálogo (Task 1).

- [ ] **Step 1: HomeScreen**

Añade el import junto a los demás de `../`:

```js
import Icono from "../components/Icono";
```

Sustituye el bloque de las líneas 51-56:

```jsx
        <TouchableOpacity
          style={[styles.btn, { marginBottom: 8 }]}
          onPress={() => navigation.navigate("Invitations")}
        >
          <Text style={styles.btnText}>📨 Mis invitaciones a equipos</Text>
        </TouchableOpacity>
```

por:

```jsx
        <TouchableOpacity
          style={[styles.btn, { marginBottom: 8, flexDirection: "row", justifyContent: "center", gap: 8 }]}
          onPress={() => navigation.navigate("Invitations")}
        >
          <Icono nombre="envelope" size={18} color={colors.pitch900} />
          <Text style={styles.btnText}>Mis invitaciones a equipos</Text>
        </TouchableOpacity>
```

**Dos avisos.** `colors.pitch900` es el color del texto de `styles.btnText`, y esta pantalla usa el tema **oscuro** (`colors`, no `lp`); el archivo ya importa `colors` en la línea 6. Y el `flexDirection` va como override local: `styles.btn` es compartido por seis pantallas y **no se toca**.

- [ ] **Step 2: RegisterStaffScreen**

Añade el import junto a los demás de `../`:

```js
import Icono from "../components/Icono";
```

Sustituye las líneas 112-116:

```jsx
      <TouchableOpacity style={styles.btnGhost} onPress={elegirDocumento}>
        <Text style={styles.btnGhostText}>
          {archivo ? `📎 ${archivo.name}` : "Adjuntar documento"}
        </Text>
      </TouchableOpacity>
```

por:

```jsx
      <TouchableOpacity style={[styles.btnGhost, { flexDirection: "row", justifyContent: "center", gap: 8 }]} onPress={elegirDocumento}>
        {!!archivo && <Icono nombre="paperclip" size={16} color={colors.chalk} />}
        <Text style={styles.btnGhostText}>{archivo ? archivo.name : "Adjuntar documento"}</Text>
      </TouchableOpacity>
```

El icono solo aparece cuando hay archivo, igual que el `📎` de antes. `colors.chalk` es el color de `styles.btnGhostText`; el archivo ya importa `colors` en la línea 8. `styles.btnGhost` es compartido por tres pantallas y **no se toca**.

- [ ] **Step 3: NotificationsScreen**

Añade el import junto a los demás de `../../`:

```js
import Icono from "../../components/Icono";
```

Sustituye la función `ICONO` de las líneas 9-16:

```js
const ICONO = (titulo = "") => {
  const t = titulo.toLowerCase();
  if (t.includes("gol")) return { icono: "football", bg: lp.green };
  if (t.includes("pago")) return { texto: "$", bg: "#E6C84F" };
  if (t.includes("torneo")) return { icono: "cuptrophy", bg: lp.green };
  if (t.includes("convocatoria")) return { texto: "!", bg: lp.red };
  return { icono: "bell", bg: lp.accent };
};
```

Las ramas de `pago` y `convocatoria` **conservan su carácter de texto**: `$` y `!` no son emoji de color y no tienen equivalente en el catálogo. No las conviertas.

Y sustituye la línea 83, dentro del círculo de color:

```jsx
                <Text style={{ color: lp.white, fontWeight: "800" }}>{ic.e}</Text>
```

por:

```jsx
                {ic.icono
                  ? <Icono nombre={ic.icono} size={16} color={lp.white} />
                  : <Text style={{ color: lp.white, fontWeight: "800" }}>{ic.texto}</Text>}
```

No toques la `✕` de la línea 90: es tipográfica y está fuera de alcance.

- [ ] **Step 4: Comprobar emojis y nombres**

```bash
cd mobile
grep -nP "[\x{1F300}-\x{1FAFF}]" src/screens/HomeScreen.js src/screens/RegisterStaffScreen.js src/screens/player/NotificationsScreen.js
echo "emojis exit=$? (1 = ninguno, correcto)"
npm run verificar-nombres
```

Esperado: sin emojis, y `OK: 33 usos de icono, todos existen` (30 previos + `envelope`, `paperclip` y las 3 claves `icono:` nuevas de `NotificationsScreen`, menos las que ya contaba — el número exacto puede variar; lo que importa es que **no haya FALLO**).

- [ ] **Step 5: Verificar sintaxis y commitear**

```bash
cd mobile && npm run verificar -- src/screens/HomeScreen.js src/screens/RegisterStaffScreen.js src/screens/player/NotificationsScreen.js
cd .. && git add mobile/src/screens/HomeScreen.js mobile/src/screens/RegisterStaffScreen.js mobile/src/screens/player/NotificationsScreen.js
git commit -m "feat(movil): iconos en invitaciones, adjuntar documento y notificaciones"
```

---

## Task 3: Resumen del partido del árbitro

**Files:**
- Modify: `mobile/src/screens/referee/RefSummaryScreen.js:68-90`

**Interfaces:**
- Consumes: `football` y `tarjeta` del catálogo, y `lp.amarilla` (Task 1).

El emoji va interpolado dentro del `<Text>`, junto al minuto y el nombre. El texto se conserva; el icono pasa a hermano en una fila.

- [ ] **Step 1: Añadir el import**

```js
import Icono from "../../components/Icono";
```

- [ ] **Step 2: Goles**

Sustituye el bloque de las líneas 71-76:

```jsx
          goles.map((g) => (
            <Text key={g.id} style={tx}>
              {g.minuto != null ? `${g.minuto}' ` : ""}⚽ {g.jugador_nombre || "—"}
              {g.subtipo && g.subtipo !== "normal" ? ` (${g.subtipo})` : ""}
              {g.jugador_secundario_nombre ? `  · asist. ${g.jugador_secundario_nombre}` : ""}
            </Text>
          ))}
```

por:

```jsx
          goles.map((g) => (
            <View key={g.id} style={filaEvento}>
              <Icono nombre="football" size={14} color={lp.textDark} />
              <Text style={[tx, { flex: 1 }]}>
                {g.minuto != null ? `${g.minuto}' ` : ""}{g.jugador_nombre || "—"}
                {g.subtipo && g.subtipo !== "normal" ? ` (${g.subtipo})` : ""}
                {g.jugador_secundario_nombre ? `  · asist. ${g.jugador_secundario_nombre}` : ""}
              </Text>
            </View>
          ))}
```

- [ ] **Step 3: Tarjetas**

Sustituye el bloque de las líneas 84-89:

```jsx
          tarjetas.map((t) => (
            <Text key={t.id} style={tx}>
              {t.minuto != null ? `${t.minuto}' ` : ""}{t.tipo === "tarjeta_roja" ? "🟥" : "🟨"} {t.jugador_nombre || "—"}
            </Text>
          ))}
```

por:

```jsx
          tarjetas.map((t) => (
            <View key={t.id} style={filaEvento}>
              <Icono nombre="tarjeta" size={14} color={t.tipo === "tarjeta_roja" ? lp.danger : lp.amarilla} />
              <Text style={[tx, { flex: 1 }]}>
                {t.minuto != null ? `${t.minuto}' ` : ""}{t.jugador_nombre || "—"}
              </Text>
            </View>
          ))}
```

La decisión roja/amarilla pasa de elegir emoji a elegir **color** sobre el mismo icono, igual que hace la web con sus clases `.ic-roja`/`.ic-amarilla`.

- [ ] **Step 4: Añadir el estilo de fila**

Junto a la constante `tx` del archivo, añade:

```js
const filaEvento = { flexDirection: "row", alignItems: "center", gap: 8, marginVertical: 2 };
```

Localiza `tx` con `grep -n "const tx" src/screens/referee/RefSummaryScreen.js` y pon la nueva justo debajo.

- [ ] **Step 5: Comprobar y commitear**

```bash
cd mobile
grep -nP "[\x{1F300}-\x{1FAFF}]" src/screens/referee/RefSummaryScreen.js; echo "emojis exit=$? (1 = ninguno)"
grep -c "✓" src/screens/referee/RefSummaryScreen.js
npm run verificar -- src/screens/referee/RefSummaryScreen.js && npm run verificar-nombres
cd .. && git add mobile/src/screens/referee/RefSummaryScreen.js
git commit -m "feat(movil): iconos en el resumen del partido"
```

Esperado: sin emojis; el `✓` de la línea 98 **sigue ahí** (cuenta ≥ 1) porque está fuera de alcance; sintaxis y nombres en verde.

---

## Task 4: Lista de eventos en vivo (cambio estructural)

**Files:**
- Modify: `mobile/src/screens/referee/RefLiveScreen.js:9-20,117`

**Interfaces:**
- Consumes: `football`, `tarjeta`, `transfer` del catálogo, y `lp.amarilla` (Task 1).
- Produces: `resumenEvento(e)` pasa a devolver `{ icono?: string, color?: string, texto: string }` en vez de una cadena.

Este es el primero de los dos cambios estructurales. `resumenEvento()` devuelve hoy una **cadena** que la línea 117 pinta como `<Text>`.

- [ ] **Step 1: Añadir el import**

```js
import Icono from "../../components/Icono";
```

- [ ] **Step 2: Sustituir el mapa de iconos y la función**

Sustituye las líneas 9-20:

```js
const ICONO = { gol: "⚽", tarjeta_amarilla: "🟨", tarjeta_roja: "🟥", cambio: "🔁" };

function resumenEvento(e) {
  const min = e.minuto != null ? `${e.minuto}' ` : "";
  if (e.tipo === "gol") {
    const extra = e.subtipo && e.subtipo !== "normal" ? ` (${e.subtipo})` : "";
    return `${min}⚽ ${e.jugador_nombre || "Gol"}${extra}`;
  }
  if (e.tipo === "cambio") return `${min}🔁 ${e.jugador_secundario_nombre || "?"} por ${e.jugador_nombre || "?"}`;
  return `${min}${ICONO[e.tipo] || ""} ${e.jugador_nombre || ""}`;
}
```

por:

```js
// Marca visual por tipo de evento. La tarjeta es el mismo icono en ambos
// colores, como en el panel web (clases .ic-amarilla / .ic-roja).
const MARCA = {
  gol: { icono: "football" },
  tarjeta_amarilla: { icono: "tarjeta", color: lp.amarilla },
  tarjeta_roja: { icono: "tarjeta", color: lp.danger },
  cambio: { icono: "transfer" },
};

// Devuelve { icono?, color?, texto }. Un tipo no contemplado sale sin icono,
// solo con su texto, igual que antes salía sin emoji.
function resumenEvento(e) {
  const min = e.minuto != null ? `${e.minuto}' ` : "";
  const marca = MARCA[e.tipo] || {};
  if (e.tipo === "gol") {
    const extra = e.subtipo && e.subtipo !== "normal" ? ` (${e.subtipo})` : "";
    return { ...marca, texto: `${min}${e.jugador_nombre || "Gol"}${extra}` };
  }
  if (e.tipo === "cambio") {
    return { ...marca, texto: `${min}${e.jugador_secundario_nombre || "?"} por ${e.jugador_nombre || "?"}` };
  }
  return { ...marca, texto: `${min}${e.jugador_nombre || ""}` };
}
```

- [ ] **Step 3: Actualizar el consumidor**

Sustituye la línea 117:

```jsx
            <Text key={e.id} style={{ color: lp.textDark, marginVertical: 3 }}>{resumenEvento(e)}</Text>
```

por:

```jsx
            <FilaEvento key={e.id} evento={e} />
```

Y añade el componente justo encima de `export default function RefLiveScreen`:

```jsx
function FilaEvento({ evento }) {
  const ev = resumenEvento(evento);
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginVertical: 3 }}>
      {!!ev.icono && <Icono nombre={ev.icono} size={14} color={ev.color || lp.textDark} />}
      <Text style={{ color: lp.textDark, flex: 1 }}>{ev.texto}</Text>
    </View>
  );
}
```

`View` ya está importado en la línea 5 de este archivo, junto a `Text` y los demás; no toques ese import.

- [ ] **Step 4: Comprobar que no queda ningún consumidor con el tipo viejo**

`resumenEvento` cambió de devolver cadena a devolver objeto. Si quedara otro sitio usándola como texto, renderizaría `[object Object]`:

```bash
cd mobile
grep -n "resumenEvento" src/screens/referee/RefLiveScreen.js
grep -rn "resumenEvento" src/ --exclude=RefLiveScreen.js; echo "otros consumidores exit=$? (1 = ninguno)"
```

Esperado: dos apariciones en `RefLiveScreen` (la definición y el uso dentro de `FilaEvento`), y ningún otro archivo.

- [ ] **Step 5: Comprobar y commitear**

```bash
cd mobile
grep -nP "[\x{1F300}-\x{1FAFF}]" src/screens/referee/RefLiveScreen.js; echo "emojis exit=$? (1 = ninguno)"
npm run verificar -- src/screens/referee/RefLiveScreen.js && npm run verificar-nombres
cd .. && git add mobile/src/screens/referee/RefLiveScreen.js
git commit -m "feat(movil): iconos en la lista de eventos en vivo"
```

---

## Task 5: Distintivos de la cancha (cambio estructural)

**Files:**
- Modify: `mobile/src/components/LineupPitch.js:14-36,128`

**Interfaces:**
- Consumes: `football`, `tarjeta` del catálogo, y `lp.amarilla` (Task 1).
- Produces: `badgesDe()` pasa a devolver `{ key, icono?, color?, letra?, texto?, veces? }[]`.

Segundo cambio estructural. `badgesDe()` devuelve hoy `{ key, texto }` con valores como `"⚽×3"`.

- [ ] **Step 1: Añadir el import**

En `mobile/src/components/LineupPitch.js`, junto a los imports existentes:

```js
import Icono from "./Icono";
```

- [ ] **Step 2: Sustituir `badgesDe`**

Sustituye las líneas 14-26:

```js
function badgesDe(resumen, jugadorId) {
  const r = resumen ? resumen[String(jugadorId)] : null;
  if (!r) return [];
  const out = [];
  if (r.goles) out.push({ key: "goles", icono: "football", veces: r.goles });
  if (r.asistencias) out.push({ key: "asist", letra: "A", veces: r.asistencias });
  if (r.amarillas) out.push({ key: "amarilla", icono: "tarjeta", color: lp.amarilla, veces: r.amarillas });
  if (r.rojas) out.push({ key: "roja", icono: "tarjeta", color: lp.rojaClara, veces: r.rojas });
  if (r.salio) out.push({ key: "sale", texto: "↓" });
  if (r.entro) out.push({ key: "entra", texto: "↑" });
  return out;
}
```

La asistencia usa `letra: "A"` y no un icono: no hay metáfora establecida para asistencias y la letra comunica lo mismo que el `🅰️` anterior. `↑` y `↓` **se quedan como texto**: son tipográficos y están fuera de alcance.

**Ojo con el color de la roja aquí:** es `lp.rojaClara`, no `lp.danger`. La cancha tiene fondo verde oscuro (`#1C6B3A`) y el rojo oscuro no se vería. En `RefSummaryScreen` y `RefLiveScreen`, que van sobre fondo claro, sí es `lp.danger`.

- [ ] **Step 3: Sustituir `Distintivos`**

Sustituye las líneas 28-36:

```jsx
function Distintivos({ badges }) {
  if (!badges.length) return null;
  return (
    <View style={estilos.badgesFila}>
      {badges.map((b) => (
        <View key={b.key} style={estilos.badge}>
          {b.icono
            ? <Icono nombre={b.icono} size={11} color={b.color || "#fff"} />
            : <Text style={estilos.badgeTexto}>{b.letra || b.texto}</Text>}
          {b.veces > 1 && <Text style={estilos.badgeTexto}>×{b.veces}</Text>}
        </View>
      ))}
    </View>
  );
}
```

- [ ] **Step 4: Ajustar los estilos**

`estilos.badge` era `{ fontSize: 11, marginHorizontal: 1 }`, un estilo de `Text`. Ahora envuelve un `View`, donde `fontSize` no aplica. Sustituye esa línea (la 128) por:

```js
  badge: { flexDirection: "row", alignItems: "center", marginHorizontal: 1 },
  badgeTexto: {
    fontSize: 11, color: "#fff", fontWeight: "700",
    textShadowColor: "rgba(0,0,0,0.7)", textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 2,
  },
```

**Blanco con sombra, no `lp.textDark`.** Los distintivos se pintan sobre la cancha, que tiene fondo verde oscuro (`estilos.cancha`, `#1C6B3A`). El estilo vecino `slotEtiqueta` —el nombre del jugador, en el mismo fondo— ya usa exactamente esta combinación por el mismo motivo. Los emoji anteriores traían sus propios colores y no tenían este problema; los iconos y el texto sí.

- [ ] **Step 5: Comprobar que no quedan consumidores del tipo viejo**

```bash
cd mobile
grep -n "badgesDe\|b.texto\|\.texto}" src/components/LineupPitch.js
grep -rn "badgesDe" src/ --exclude=LineupPitch.js; echo "otros consumidores exit=$? (1 = ninguno)"
```

Esperado: `badgesDe` aparece en su definición y en las dos llamadas (líneas ~73 y ~85), y en ningún otro archivo. Las dos llamadas pasan el resultado a `<Distintivos badges={…}>`, que ya está actualizado, así que **no hay que tocarlas**.

- [ ] **Step 6: Comprobar y commitear**

```bash
cd mobile
grep -nP "[\x{1F300}-\x{1FAFF}]" src/components/LineupPitch.js; echo "emojis exit=$? (1 = ninguno)"
grep -c "↑\|↓" src/components/LineupPitch.js
npm run verificar -- src/components/LineupPitch.js && npm run verificar-nombres
cd .. && git add mobile/src/components/LineupPitch.js
git commit -m "feat(movil): iconos en los distintivos de la cancha"
```

Esperado: sin emojis de color; las flechas `↑ ↓` **siguen ahí** (cuenta ≥ 2) porque están fuera de alcance.

---

## Task 6: Verificación de rama y checklist de dispositivo

**Files:**
- Create: `docs/superpowers/checklist-iconos-eventos.md`

- [ ] **Step 1: Verificar sintaxis de todo lo tocado**

```bash
cd mobile && npm run verificar -- \
  scripts/generar-iconos.cjs \
  scripts/verificar-iconos.cjs \
  scripts/verificar-nombres-iconos.cjs \
  src/publicTheme.js \
  src/components/LineupPitch.js \
  src/screens/HomeScreen.js \
  src/screens/RegisterStaffScreen.js \
  src/screens/player/NotificationsScreen.js \
  src/screens/referee/RefLiveScreen.js \
  src/screens/referee/RefSummaryScreen.js
echo "sintaxis exit=$?"
npm run verificar-iconos && npm run verificar-nombres
```

Esperado: diez `OK`, `sintaxis exit=0`, `OK: 20 iconos válidos`, y `verificar-nombres` sin ningún FALLO.

- [ ] **Step 2: Comprobar que solo quedan los 8 tipográficos**

```bash
cd mobile
echo "--- emojis de color (debe estar vacio) ---"
grep -rnP "[\x{1F300}-\x{1FAFF}]" src/ App.js
echo "--- tipograficos que SI deben seguir (esperado: 8 lineas) ---"
grep -rnP "[✓✕↑↓→]" src/ App.js | wc -l
```

Esperado: la primera lista vacía; la segunda, **8**. Si hay menos de 8, se tocó algo fuera de alcance.

- [ ] **Step 3: Confirmar que no se tocó el backend**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol
git diff --name-only main...HEAD | grep -E '^(api|web)/'; echo "coincidencias: $?"
```

Esperado: sin salida y `coincidencias: 1`. Fíate de que **no haya salida de texto**. Si aparece algo, **para**.

- [ ] **Step 4: Suite de Python**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol/api && .venv/bin/python -m pytest -q 2>&1 | tail -5
```

Esperado: `233 passed`. **Tarda ~12,5 minutos**: córrela **en primer plano** con timeout de 900000 ms. No la lances en segundo plano esperando una notificación — no llega. Si el número no es 233, repórtalo tal cual.

- [ ] **Step 5: Escribir el checklist**

Crea `docs/superpowers/checklist-iconos-eventos.md`:

```markdown
# Checklist de validación en dispositivo — iconos de eventos y restantes

Lo estático está verificado: los archivos parsean, los 20 iconos pasan sus
aserciones, todos los nombres de icono existen, y los 233 tests de Python siguen
en verde.

**Lo que esto busca:** dos funciones cambiaron su tipo de retorno
(`resumenEvento` y `badgesDe`). Es el primer trabajo de las tres tandas de iconos
que puede romper comportamiento, no solo aspecto.

## Preparación

1. Backend arriba: `docker compose up -d`. Si es una BD nueva, siembra los datos
   demo: `docker compose exec api python -m app.seed`.
2. `cd mobile && npx expo start` (modo LAN, **sin** `--tunnel`) y escanea el QR.
3. Si el bundle sale raro tras el cambio de iconos: `npx expo start -c`.

> **Necesitas un partido con eventos.** Sin goles, tarjetas ni cambios no se
> puede validar nada de lo estructural. Entra como **arbitro@demo.com /
> demo1234**, abre un partido asignado, inícialo y registra: dos goles del mismo
> jugador, una tarjeta amarilla, una roja a otro jugador, y un cambio.

## 1. Lista de eventos en vivo — ÁRBITRO
- [ ] Cada evento de la lista muestra su icono a la izquierda: **balón** en goles,
      **rectángulo amarillo** o **rojo** en tarjetas, **flechas de intercambio** en
      cambios.
- [ ] El texto sigue completo: minuto, nombre del jugador, y en el cambio "X por Y".
- [ ] Ningún renglón muestra `[object Object]`. Si aparece, un consumidor quedó
      con el tipo viejo.

## 2. Alineaciones (distintivos) — ÁRBITRO
- [ ] Abre **Ver alineaciones** desde el partido en vivo.
- [ ] El goleador con dos goles muestra **balón ×2**, no "⚽×2" ni solo el balón.
- [ ] El amonestado muestra el **rectángulo amarillo**; el expulsado, el **rojo**.
- [ ] Si hay asistencia, aparece una **"A"** (con ×N si hay más de una).
- [ ] Las flechas **↑ ↓** de entra/sale siguen siendo flechas: no se tocaron.
- [ ] Con cuatro distintivos sobre un mismo jugador, no se salen de la foto ni se
      solapan de forma ilegible.
- [ ] **Contraste:** todos los distintivos se leen sobre el verde de la cancha. El
      balón y la "A" van en blanco con sombra, la amarilla en amarillo y la roja en
      un rojo claro, a propósito. Si alguno se pierde contra el fondo, dilo: los
      emoji de antes traían su propio color y estos no.

## 3. Resumen del partido — ÁRBITRO
- [ ] Firma el acta y abre el resumen. Las secciones **Goles** y **Tarjetas**
      muestran icono a la izquierda y el texto a la derecha, sin partirse.
- [ ] El `✓` de acta firmada sigue siendo un `✓`: está fuera de alcance.

## 4. Notificaciones — JUGADOR
- [ ] Entra como **jugador@demo.com / demo1234** → campana de INICIO.
- [ ] Los avisos de gol muestran un **balón**, los de torneo una **copa**, y el
      resto una **campana**, dentro de su círculo de color.
- [ ] Los avisos de **pago** siguen mostrando `$` y los de **convocatoria** `!`.
      Es lo esperado: no son emoji y quedan fuera de alcance.
- [ ] La `✕` de descartar sigue siendo una `✕`.

## 5. Los dos sueltos
- [ ] **Mi panel** (jugador): el botón "Mis invitaciones a equipos" lleva un
      **sobre** delante, sobre el fondo lima.
- [ ] **Crear cuenta → Entrenador/Árbitro**: pulsa "Adjuntar documento" y elige un
      archivo. Al seleccionarlo aparece un **clip** y el nombre del archivo. Antes
      de elegir, el botón dice solo "Adjuntar documento", sin icono.

## Si algo falla
Anota **rol, pantalla y qué viste** (o captura). Lo más probable:
1. `[object Object]` en la lista de eventos → un consumidor de `resumenEvento`
   quedó con el tipo viejo.
2. Distintivo sin icono pero con el ×N → el nombre de icono no existe; revisa
   `mobile/src/components/iconos-datos.json`.
3. Tarjeta del color equivocado → revisa el ternario de `t.tipo === "tarjeta_roja"`.
4. Hueco vacío donde va un icono → nombre mal escrito.
5. "Unable to resolve module" → caché de Metro; `npx expo start -c`.
```

- [ ] **Step 6: Commitear el checklist**

```bash
git add docs/superpowers/checklist-iconos-eventos.md
git commit -m "docs(movil): checklist de validacion de iconos de eventos"
```

---

## Auto-revisión del plan

**Cobertura del spec:**

| Requisito del spec | Tarea |
|---|---|
| Catálogo de 16 a 20 (`transfer`, `tarjeta`, `envelope`, `paperclip`) | Task 1, Steps 2-4 |
| `tarjeta` convertido de `<rect>` a path, sin tocar `Icono.js` | Task 1, Step 2 (`LITERALES`) |
| `lp.amarilla = "#f2b53c"` | Task 1, Step 6 |
| `verificar-iconos` a 20 claves | Task 1, Step 5 |
| Verificador de nombres ampliado a 3 formas + acotado a `<Icono>` | Task 1, Steps 7-8 |
| `📨` HomeScreen, `📎` RegisterStaffScreen | Task 2, Steps 1-2 |
| `NotificationsScreen`: 3 de 5 ramas, `$` y `!` intactos | Task 2, Step 3 |
| `RefSummaryScreen` goles y tarjetas | Task 3 |
| `RefLiveScreen`: `resumenEvento` devuelve objeto | Task 4 |
| `LineupPitch`: `badgesDe` con icono y multiplicador; "A" de asistencia | Task 5 |
| Los 8 tipográficos NO se tocan | Global Constraints + Task 6, Step 2 (comprobación activa) |
| Sin cambios en `api/` ni `web/` | Task 6, Step 3 |
| Suite Python en 233 | Task 6, Step 4 |
| Validación en dispositivo con datos de partido | Task 6, Steps 5-6 |

Sin huecos.

**Consistencia de nombres** (verificada entre tareas): las 4 claves nuevas se escriben igual en el generador (Task 1), en `ESPERADOS` (Task 1 Step 5) y en las pantallas (Tasks 2-5): `transfer`, `tarjeta`, `envelope`, `paperclip`. `lp.amarilla` se define en Task 1 Step 6 y se consume en Tasks 3, 4 y 5. Los campos del objeto de `resumenEvento` (`icono`/`color`/`texto`) coinciden entre Task 4 Step 2 y Step 3. Los de `badgesDe` (`key`/`icono`/`color`/`letra`/`texto`/`veces`) coinciden entre Task 5 Step 2 y Step 3.

**Nota sobre el recuento de `verificar-nombres`:** el script imprime cuántos usos validó, y ese número **crece en cada tarea** (30 tras la Task 1, más a medida que se añaden iconos). El plan no fija el número exacto en las Tasks 2-5 a propósito: lo que hay que comprobar es que **no aparezca ningún FALLO**, no que coincida una cifra. Solo la Task 1 Step 8 fija un número (30), porque ahí el código aún no ha cambiado.

**Tres correcciones aplicadas al escribir el plan**, todas descubiertas verificando contra el código en vez de suponerlo:

1. **Los distintivos de la cancha se habrían pintado invisibles.** El plan usaba `lp.textDark` para el icono y el texto, pero `LineupPitch` los dibuja sobre `estilos.cancha`, de fondo **verde oscuro `#1C6B3A`**. El estilo vecino `slotEtiqueta` ya usa blanco con sombra por ese mismo motivo. Corregido a blanco con sombra. Los emoji anteriores traían su propio color y no tenían el problema.
2. **El rojo de la tarjeta necesita dos valores.** El mismo icono aparece sobre fondo claro (listas del árbitro) y sobre el verde de la cancha. `lp.danger` (`#c0392b`) contrasta bien sobre claro y mal sobre el verde, así que la paleta gana también `rojaClara` (`#ff5a5a`, el mismo `--danger` que el panel web usa sobre fondo oscuro). El plan fija qué va dónde en una tabla.
3. **`View` ya estaba importado** en `RefLiveScreen` (línea 5). El plan pedía comprobarlo; ahora lo afirma.

**Verificado ejecutando, no razonando:** la ampliación del generador (Task 1 Steps 2-3) se probó tal como queda escrita y produce los 15 iconos con los recuentos exactos, incluida la `tarjeta` derivada del `<rect>`. Las tres expresiones regulares del verificador ampliado (Task 1 Step 7) se probaron contra el código real: detectan 30 usos, frente a los 18 de la versión actual, sin falsos positivos de `<Avatar>`.

**Riesgo conocido, sin mitigar en el plan:** el Step 1 de la Task 1 depende de `npm pack reicon@1.1.103` (red). Si falla, la tarea queda bloqueada; no hay copia de los paths en el repo. Es el mismo patrón de los PRs #18, #21 y #22, aceptado allí.
