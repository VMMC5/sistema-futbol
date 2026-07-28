# Iconos en la barra de navegación y en las pantallas restantes (móvil) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poner iconos en la barra de navegación de los cuatro roles y sustituir los emojis que quedan en cuatro pantallas.

**Architecture:** El catálogo `iconos-datos.json` pasa de 5 a 16 entradas mediante un script generador (sin transcripción manual); `Icono.js` no cambia. La barra de navegación deja de pintar un punto y declara un icono por pestaña.

**Tech Stack:** React Native 0.74.5 / Expo SDK 51, `react-native-svg` 15.2.0, `@react-navigation/bottom-tabs`. Sin backend.

**Spec:** `docs/superpowers/specs/2026-07-28-iconos-navegacion-y-pantallas-design.md`

## Global Constraints

- **No se toca `api/` ni `web/`.** La suite de Python debe seguir en **233 en verde**. Tarda **~12,5 minutos**, no 4.
- **Verificación:** `cd mobile && npm run verificar <archivos…>` y `npm run verificar-iconos`. **Prohibido `npx babel`**: resuelve al paquete `babel` v6 deprecado del caché de npx (no a `@babel/cli`, que no está instalado) y hace fallar archivos válidos.
- **El paquete npm `reicon` nunca entra en `node_modules` ni en `package.json`.** Se descarga a scratchpad y se descarta.
- **`Icono.js` NO se modifica.** Su contrato (`{ nombre, size = 18, color }`) ya cubre todos los casos nuevos. Si algo parece exigir cambiarlo, para y reporta.
- **Claves de icono:** minúsculas, sin separadores (`creditcard`, `clipboardlist`, `docadd`).
- **`iconos-datos.json` debe acabar con exactamente 16 claves.** `verificar-iconos.cjs` valida que no falte **ni sobre** ninguna.
- **Idioma:** comentarios, nombres y textos de UI en español.
- **Rama:** `feat/iconos-navegacion`, ya creada. El spec está commiteado en `ca9c2ca`.
- **No hay runner de tests JS.** Nada cubre `mobile/`. Un defecto de ejecución no lo detecta ninguna verificación estática; solo la validación en dispositivo.

### Riesgo dominante de esta tanda

Once claves nuevas repartidas por cuatro barras y cuatro pantallas. **Una errata en un nombre de icono no da error: da un hueco invisible.** Por eso `verificar-iconos.cjs` valida el conjunto exacto de claves, la Task 2 incluye una comprobación cruzada de que todo `nombre=` usado en el código existe en el JSON, y el checklist recorre pestaña por pestaña.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `mobile/scripts/generar-iconos.cjs` | **Crear.** Genera las 11 entradas nuevas desde el macro web y el paquete reicon. |
| `mobile/src/components/iconos-datos.json` | **Modificar.** De 5 a 16 iconos. |
| `mobile/scripts/verificar-iconos.cjs` | **Modificar.** `ESPERADOS` de 5 a 16 claves. |
| `mobile/App.js` | **Modificar.** Se elimina `Punto`; cada `Tab.Screen` declara su `tabBarIcon`. |
| `mobile/src/screens/public/TorneosScreen.js` | **Modificar.** `🏆` → `cuptrophy`. |
| `mobile/src/screens/player/PlayerHomeScreen.js` | **Modificar.** `📊`→`chart`, `📅`→`calendar`; los dos botones pasan a fila. |
| `mobile/src/screens/coach/CoachHomeScreen.js` | **Modificar.** Rejilla: `👥📝📋📅` → `people/docadd/clipboardlist/calendar`. |
| `mobile/src/screens/player/ReservarScreen.js` | **Modificar.** El `📍` sale del `placeholder`; el buscador pasa a fila. |
| `docs/superpowers/checklist-iconos-navegacion.md` | **Crear.** Checklist de validación en dispositivo. |

---

## Task 1: Ampliar el catálogo de 5 a 16 iconos

**Files:**
- Create: `mobile/scripts/generar-iconos.cjs`
- Modify: `mobile/src/components/iconos-datos.json`
- Modify: `mobile/scripts/verificar-iconos.cjs`

**Interfaces:**
- Produces: `iconos-datos.json` con 16 claves. Las 11 nuevas: `cuptrophy`, `chart`, `calendar`, `people`, `football`, `home`, `user`, `history`, `clipboardlist`, `docadd`, `location`. Formato por entrada: `{ d: string[], trazo?: true, parImpar?: true }`.

**Por qué un generador y no transcripción a mano:** `calendar` trae 7 paths y `people` 6, algunos de más de 1000 caracteres. Perder uno al copiar no da error — da un icono incompleto que ninguna verificación estática detecta. El script elimina ese riesgo y deja constancia de la procedencia de cada icono.

- [ ] **Step 1: Descargar reicon a scratchpad**

```bash
mkdir -p /tmp/reicon-gen && cd /tmp/reicon-gen && \
  npm pack reicon@1.1.103 >/dev/null 2>&1 && tar xzf reicon-*.tgz && \
  ls package/icons/Home.js package/icons/User.js package/icons/History.js \
     package/icons/ClipboardList.js package/icons/DocAdd.js package/icons/Pin.js
```

Esperado: las seis rutas listadas sin error. **No instales `reicon` en el proyecto.**

- [ ] **Step 2: Crear el generador**

Crea `mobile/scripts/generar-iconos.cjs`:

```js
// Genera las entradas de iconos-datos.json desde sus dos fuentes:
//   - el macro Jinja de la web (web/app/templates/_iconos.html), para que movil
//     y web pinten el mismo path del mismo concepto
//   - el paquete npm reicon, descargado aparte (NO es dependencia del proyecto)
//
// Uso:  node scripts/generar-iconos.cjs <dir-del-paquete-reicon>
// Ej.:  node scripts/generar-iconos.cjs /tmp/reicon-gen/package
//
// Imprime el JSON por stdout. No escribe nada: revisa y redirige tu mismo.
const fs = require("fs");
const path = require("path");

const RAIZ_REPO = path.join(__dirname, "..", "..");
const dirReicon = process.argv[2];
if (!dirReicon) {
  console.error("Falta el directorio del paquete reicon. Ver la cabecera del script.");
  process.exit(1);
}

// Del macro de la web: mismo concepto, mismo path que el panel.
const DESDE_WEB = ["cuptrophy", "chart", "calendar", "people", "football"];
// De reicon: clave en el JSON -> nombre del archivo del paquete.
const DESDE_REICON = {
  home: "Home",
  user: "User",
  history: "History",
  clipboardlist: "ClipboardList",
  docadd: "DocAdd",
  location: "Pin",   // el "location" del macro web usa circle/line/g: no vale aqui
};

function paths(svg) {
  return [...svg.matchAll(/\sd="([^"]+)"/g)].map((m) => m[1]);
}

function entrada(svg) {
  const e = { d: paths(svg) };
  if (svg.includes('stroke="currentColor"') || svg.includes('stroke="#')) e.trazo = true;
  if (svg.includes('fill-rule="evenodd"')) e.parImpar = true;
  return e;
}

const macro = fs.readFileSync(path.join(RAIZ_REPO, "web/app/templates/_iconos.html"), "utf8");
const salida = {};

for (const nombre of DESDE_WEB) {
  const m = macro.match(new RegExp(`"${nombre}": "(.*?)",\\n`, "s"));
  if (!m) { console.error(`No encontre "${nombre}" en el macro web`); process.exit(1); }
  salida[nombre] = entrada(m[1].replace(/\\"/g, '"'));
}

for (const [clave, archivo] of Object.entries(DESDE_REICON)) {
  const src = fs.readFileSync(path.join(dirReicon, "icons", `${archivo}.js`), "utf8");
  const b64 = src.match(/base64,([A-Za-z0-9+/=]*)/);
  if (!b64) { console.error(`No encontre el SVG de ${archivo}`); process.exit(1); }
  salida[clave] = entrada(Buffer.from(b64[1], "base64").toString("utf8"));
}

console.log(JSON.stringify(salida, null, 2));
```

- [ ] **Step 3: Generar y comprobar los recuentos**

```bash
cd mobile
node scripts/generar-iconos.cjs /tmp/reicon-gen/package > /tmp/iconos-nuevos.json
node -e '
const d = require("/tmp/iconos-nuevos.json");
const ESPERADO = { cuptrophy:[2,false], chart:[1,false], calendar:[7,false], people:[6,true],
  football:[1,false], home:[2,false], user:[2,false], history:[1,false],
  clipboardlist:[1,false], docadd:[1,false], location:[1,false] };
let malos = 0;
for (const [k,[n,trazo]] of Object.entries(ESPERADO)) {
  const e = d[k];
  const okN = e && e.d.length === n, okT = e && !!e.trazo === trazo;
  if (!okN || !okT) { console.log(`FALLO ${k}: paths=${e && e.d.length} (esperado ${n}), trazo=${e && !!e.trazo} (esperado ${trazo})`); malos++; }
}
console.log(malos ? `${malos} discrepancias` : `OK: 11 iconos con los paths esperados`);
process.exit(malos ? 1 : 0);'
```

Esperado: `OK: 11 iconos con los paths esperados`. Si algún recuento no cuadra, **para y reporta**: significa que la fuente cambió y los datos no son los que el spec verificó.

- [ ] **Step 4: Fusionar en iconos-datos.json**

```bash
cd mobile
node -e '
const fs = require("fs");
const viejos = require("./src/components/iconos-datos.json");
const nuevos = require("/tmp/iconos-nuevos.json");
const choque = Object.keys(nuevos).filter(k => k in viejos);
if (choque.length) { console.error("Claves duplicadas: " + choque.join(", ")); process.exit(1); }
const todos = { ...viejos, ...nuevos };
fs.writeFileSync("./src/components/iconos-datos.json", JSON.stringify(todos, null, 2) + "\n");
console.log("escrito, total de iconos: " + Object.keys(todos).length);'
```

Esperado: `escrito, total de iconos: 16`.

- [ ] **Step 5: Ampliar el verificador a 16 claves**

En `mobile/scripts/verificar-iconos.cjs`, sustituye la línea de `ESPERADOS` por:

```js
const ESPERADOS = [
  "edit", "creditcard", "lock", "logout", "bell",
  "cuptrophy", "chart", "calendar", "people", "football",
  "home", "user", "history", "clipboardlist", "docadd", "location",
];
```

No toques el resto del script: sus aserciones (path no vacío, empieza por `M`, sin colores incrustados, sin claves de más) siguen valiendo.

- [ ] **Step 6: Ejecutar los verificadores**

```bash
cd mobile && npm run verificar-iconos && npm run verificar -- scripts/generar-iconos.cjs
```

Esperado: `OK: 16 iconos válidos` y `OK scripts/generar-iconos.cjs`.

- [ ] **Step 7: Commit**

```bash
git add mobile/scripts/generar-iconos.cjs mobile/scripts/verificar-iconos.cjs mobile/src/components/iconos-datos.json
git commit -m "feat(movil): amplia el catalogo de iconos de 5 a 16"
```

---

## Task 2: Iconos en la barra de navegación

**Files:**
- Modify: `mobile/App.js`

**Interfaces:**
- Consumes: las 16 claves de `iconos-datos.json` (Task 1) y `Icono` de `mobile/src/components/Icono.js`.

- [ ] **Step 1: Importar Icono**

En `mobile/App.js`, junto a los demás imports de `./src/`, añade:

```js
import Icono from "./src/components/Icono";
```

- [ ] **Step 2: Eliminar la función Punto**

Borra por completo:

```js
// Indicador (puntito) de cada pestaña, como en el mockup.
function Punto({ focused }) {
  return <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: focused ? lp.accent : "#C7C2B5" }} />;
}
```

Y en los **cuatro** `Tab.Navigator` (`PublicTabs`, `CoachTabs`, `RefereeTabs`, `PlayerTabs`), borra de su bloque `screenOptions` esta línea:

```js
        tabBarIcon: ({ focused }) => <Punto focused={focused} />,
```

**Ajusta el import de `react-native`.** Verificado: `View` lo usaba **solo** `Punto`; `LoginButton` usa `Text` y `TouchableOpacity`. Al borrar `Punto`, `View` queda sin uso. La línea 3 de `App.js`:

```js
import { View, Text, TouchableOpacity } from "react-native";
```

pasa a:

```js
import { Text, TouchableOpacity } from "react-native";
```

- [ ] **Step 3: Declarar el icono en cada pestaña**

React Navigation inyecta `color` ya resuelto (`lp.accent` si está activa, `lp.textMuted` si no), configurado en los `screenOptions` que no se tocan. `size={22}`, no los 18 por defecto: el área táctil de una pestaña es mayor.

En `PublicTabs`:

```jsx
      <Tab.Screen name="Inicio" component={InicioScreen} options={{ title: "INICIO", tabBarIcon: ({ color }) => <Icono nombre="home" size={22} color={color} /> }} />
      <Tab.Screen name="Torneos" component={TorneosScreen} options={{ title: "TORNEOS", tabBarIcon: ({ color }) => <Icono nombre="cuptrophy" size={22} color={color} /> }} />
```

En `CoachTabs`:

```jsx
      <Tab.Screen name="Inicio" component={CoachHomeScreen} options={{ title: "INICIO", tabBarIcon: ({ color }) => <Icono nombre="home" size={22} color={color} /> }} />
      <Tab.Screen name="Equipos" component={TeamListScreen} options={{ title: "MIS EQUIPOS", tabBarIcon: ({ color }) => <Icono nombre="people" size={22} color={color} /> }} />
      <Tab.Screen name="Torneos" component={TorneosScreen} options={{ title: "TORNEOS", tabBarIcon: ({ color }) => <Icono nombre="cuptrophy" size={22} color={color} /> }} />
      <Tab.Screen name="Perfil" component={PerfilScreen} options={{ title: "PERFIL", tabBarIcon: ({ color }) => <Icono nombre="user" size={22} color={color} /> }} />
```

En `RefereeTabs`:

```jsx
      <Tab.Screen name="Partidos" component={RefMatchesScreen} options={{ title: "PARTIDOS ASIGNADOS", tabBarIcon: ({ color }) => <Icono nombre="football" size={22} color={color} /> }} />
      <Tab.Screen name="Historial" component={RefHistoryScreen} options={{ title: "HISTORIAL", tabBarIcon: ({ color }) => <Icono nombre="history" size={22} color={color} /> }} />
      <Tab.Screen name="Perfil" component={PerfilScreen} options={{ title: "PERFIL", tabBarIcon: ({ color }) => <Icono nombre="user" size={22} color={color} /> }} />
```

En `PlayerTabs`:

```jsx
      <Tab.Screen name="Inicio" component={PlayerHomeScreen} options={{ title: "INICIO", tabBarIcon: ({ color }) => <Icono nombre="home" size={22} color={color} /> }} />
      <Tab.Screen name="Torneos" component={TorneosScreen} options={{ title: "TORNEOS", tabBarIcon: ({ color }) => <Icono nombre="cuptrophy" size={22} color={color} /> }} />
      <Tab.Screen name="Reservar" component={ReservarScreen} options={{ title: "RESERVAR CANCHA", tabBarIcon: ({ color }) => <Icono nombre="calendar" size={22} color={color} /> }} />
      <Tab.Screen name="Perfil" component={PlayerProfileScreen} options={{ title: "MI PERFIL", tabBarIcon: ({ color }) => <Icono nombre="user" size={22} color={color} /> }} />
```

- [ ] **Step 4: Comprobar que no queda rastro de Punto**

```bash
cd mobile && grep -n "Punto" App.js; echo "exit=$? (1 = ninguno, correcto)"
grep -c "tabBarIcon" App.js
```

Esperado: sin coincidencias de `Punto` (`exit=1`), y **13** ocurrencias de `tabBarIcon` (2+4+3+4 pestañas).

- [ ] **Step 5: Comprobación cruzada — todo nombre de icono usado existe**

Esta es la red contra la errata invisible. Ejecútala desde `mobile/`:

```bash
cd mobile
node -e '
const fs = require("fs"), path = require("path");
const iconos = new Set(Object.keys(require("./src/components/iconos-datos.json")));
const archivos = [];
(function walk(d) {
  for (const f of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, f.name);
    if (f.isDirectory()) walk(p); else if (p.endsWith(".js")) archivos.push(p);
  }
})("src");
archivos.push("App.js");
let malos = 0;
for (const a of archivos) {
  const txt = fs.readFileSync(a, "utf8");
  for (const m of txt.matchAll(/nombre=\"([a-z]+)\"/g)) {
    if (!iconos.has(m[1])) { console.log(`FALLO ${a}: nombre=\"${m[1]}\" no existe en iconos-datos.json`); malos++; }
  }
}
console.log(malos ? `${malos} nombres invalidos` : "OK: todos los nombres de icono existen");
process.exit(malos ? 1 : 0);'
```

Esperado: `OK: todos los nombres de icono existen`.

- [ ] **Step 6: Verificar sintaxis y commitear**

```bash
cd mobile && npm run verificar -- App.js
cd .. && git add mobile/App.js && git commit -m "feat(movil): iconos en la barra de navegacion de los cuatro roles"
```

---

## Task 3: Iconos en TorneosScreen, PlayerHomeScreen y CoachHomeScreen

**Files:**
- Modify: `mobile/src/screens/public/TorneosScreen.js:53`
- Modify: `mobile/src/screens/player/PlayerHomeScreen.js:58-65`
- Modify: `mobile/src/screens/coach/CoachHomeScreen.js:10-15,70-75`

**Interfaces:**
- Consumes: `Icono`, y las claves `cuptrophy`, `chart`, `calendar`, `people`, `docadd`, `clipboardlist`.

- [ ] **Step 1: TorneosScreen**

Añade el import junto a los demás de `../../`:

```js
import Icono from "../../components/Icono";
```

Sustituye la línea 53:

```jsx
            <View style={ls.iconCircle}><Text style={ls.iconText}>🏆</Text></View>
```

por:

```jsx
            <View style={ls.iconCircle}><Icono nombre="cuptrophy" size={18} color={lp.greenText} /></View>
```

`lp` ya está importado (línea 7: `import { lp, ls } from "../../publicTheme";`), no toques el import.

**Borra también `ls.iconText`** de `mobile/src/publicTheme.js` (línea 43): verificado que esta línea 53 era su **único** consumidor en todo `src/`, así que queda muerto tras el cambio. `ls.iconCircle` **sí se conserva** — el círculo verde sigue ahí. Confirma con `grep -rn "iconText" src/` que no queda ninguna referencia antes de commitear.

- [ ] **Step 2: PlayerHomeScreen**

Añade el import:

```js
import Icono from "../../components/Icono";
```

Sustituye los dos botones:

```jsx
      <TouchableOpacity style={btn.primary} onPress={() => navigation.navigate("PlayerStats")}>
        <Text style={btn.primaryText}>📊 Ver mis estadísticas</Text>
      </TouchableOpacity>

      <TouchableOpacity style={btn.ghost} onPress={() => navigation.navigate("PlayerCalendar")}>
        <Text style={btn.ghostText}>📅 Próximos partidos</Text>
      </TouchableOpacity>
```

por:

```jsx
      <TouchableOpacity style={btn.primary} onPress={() => navigation.navigate("PlayerStats")}>
        <Icono nombre="chart" size={18} color={lp.white} />
        <Text style={btn.primaryText}>Ver mis estadísticas</Text>
      </TouchableOpacity>

      <TouchableOpacity style={btn.ghost} onPress={() => navigation.navigate("PlayerCalendar")}>
        <Icono nombre="calendar" size={18} color={lp.green} />
        <Text style={btn.ghostText}>Próximos partidos</Text>
      </TouchableOpacity>
```

Los botones tienen hoy `alignItems: "center"` pero apilan en columna. Para que icono y texto queden en fila, cambia en el bloque `const btn` (líneas 96-101) las dos entradas de contenedor:

```js
  primary: { backgroundColor: lp.accent, borderRadius: 12, paddingVertical: 15, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 10 },
  ghost: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingVertical: 15, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
```

`primaryText` y `ghostText` no cambian. El color del icono sigue al del texto de su botón: blanco en el primario, verde en el fantasma.

- [ ] **Step 3: CoachHomeScreen**

Añade el import:

```js
import Icono from "../../components/Icono";
```

Sustituye el array `ACCIONES` (líneas 10-15):

```js
const ACCIONES = [
  { icono: "people", label: "Mis equipos", destino: "Equipos" },
  { icono: "docadd", label: "Inscribir", proximamente: true },
  { icono: "clipboardlist", label: "Alineación", destino: "LineupMatches" },
  { icono: "calendar", label: "Reservar", proximamente: true },
];
```

Y en el render (líneas 70-75), sustituye:

```jsx
            <Text style={cs.gridIcon}>{a.icon}</Text>
```

por:

```jsx
            <View style={{ marginBottom: 8 }}><Icono nombre={a.icono} size={24} color={lp.gold} /></View>
```

`cs.gridIcon` era `{ fontSize: 22, marginBottom: 8 }`; el `fontSize` no aplica a un componente, así que el margen se traslada al `View`. `lp` ya está importado (línea 8: `import { cs, lp, ls } from "../../publicTheme";`).

**`cs.gridIcon` queda sin uso tras este cambio.** A diferencia de `ls.iconText`, **déjalo**: `cs` es el tema del panel del entrenador y no lo he auditado entero. Anótalo como deuda menor en tu informe en vez de borrarlo a ciegas.

- [ ] **Step 4: Comprobar que no quedan emojis en los tres archivos**

```bash
cd mobile && grep -nP "[\x{1F300}-\x{1FAFF}]" \
  src/screens/public/TorneosScreen.js \
  src/screens/player/PlayerHomeScreen.js \
  src/screens/coach/CoachHomeScreen.js
echo "exit=$? (1 = sin emojis, correcto)"
```

- [ ] **Step 5: Comprobación cruzada de nombres de icono**

Repite exactamente el mismo comando del Step 5 de la Task 2 (el script de `node -e` que recorre `src/` y `App.js`). Esperado: `OK: todos los nombres de icono existen`.

- [ ] **Step 6: Verificar sintaxis y commitear**

```bash
cd mobile && npm run verificar -- \
  src/screens/public/TorneosScreen.js \
  src/screens/player/PlayerHomeScreen.js \
  src/screens/coach/CoachHomeScreen.js
cd .. && git add mobile/src/screens/public/TorneosScreen.js mobile/src/screens/player/PlayerHomeScreen.js mobile/src/screens/coach/CoachHomeScreen.js
git commit -m "feat(movil): iconos en torneos, inicio del jugador y rejilla del entrenador"
```

---

## Task 4: El buscador de sede de ReservarScreen

**Files:**
- Modify: `mobile/src/screens/player/ReservarScreen.js:87-94`

**Interfaces:**
- Consumes: `Icono` y la clave `location`.

Es el único cambio estructural de la tanda. El `📍` está dentro del `placeholder`, que es un **string**: no admite un componente. Hay que sacar el icono fuera del `TextInput`.

- [ ] **Step 1: Añadir el import**

```js
import Icono from "../../components/Icono";
```

- [ ] **Step 2: Reestructurar el buscador**

Sustituye:

```jsx
      <View style={{ backgroundColor: lp.white, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 4, marginBottom: 8 }}>
        <TextInput
          style={{ color: lp.textDark, paddingVertical: 12, fontSize: 15 }}
          placeholder="📍 Buscar sede" placeholderTextColor={lp.textMuted}
          value={buscar} onChangeText={(t) => { setBuscar(t); setSedeSel(null); }}
        />
      </View>
```

por:

```jsx
      {/* El icono va fuera del TextInput: placeholder solo admite texto. */}
      <View style={{ backgroundColor: lp.white, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 4, marginBottom: 8, flexDirection: "row", alignItems: "center", gap: 10 }}>
        <Icono nombre="location" size={18} color={lp.textMuted} />
        <TextInput
          style={{ flex: 1, color: lp.textDark, paddingVertical: 12, fontSize: 15 }}
          placeholder="Buscar sede" placeholderTextColor={lp.textMuted}
          value={buscar} onChangeText={(t) => { setBuscar(t); setSedeSel(null); }}
        />
      </View>
```

Tres cambios: el contenedor pasa a fila, el icono entra como hermano, y el `TextInput` gana `flex: 1` para ocupar el resto. El `placeholder` pierde el emoji. **No toques `value`, `onChangeText` ni el resto de la pantalla.**

- [ ] **Step 3: Comprobar el resultado**

```bash
cd mobile
grep -n "📍" src/screens/player/ReservarScreen.js; echo "emoji exit=$? (1 = fuera, correcto)"
grep -n "flex: 1" src/screens/player/ReservarScreen.js | head -3
grep -c "setSedeSel(null)" src/screens/player/ReservarScreen.js
```

Esperado: sin coincidencias del emoji; el `flex: 1` presente; y `setSedeSel(null)` sigue apareciendo (la lógica de búsqueda intacta).

- [ ] **Step 4: Verificar sintaxis y commitear**

```bash
cd mobile && npm run verificar -- src/screens/player/ReservarScreen.js
cd .. && git add mobile/src/screens/player/ReservarScreen.js
git commit -m "feat(movil): icono de sede fuera del placeholder del buscador"
```

---

## Task 5: Verificación de rama y checklist de dispositivo

**Files:**
- Create: `docs/superpowers/checklist-iconos-navegacion.md`

- [ ] **Step 1: Verificar sintaxis de todo lo tocado**

```bash
cd mobile && npm run verificar -- \
  App.js \
  scripts/generar-iconos.cjs \
  src/screens/public/TorneosScreen.js \
  src/screens/player/PlayerHomeScreen.js \
  src/screens/player/ReservarScreen.js \
  src/screens/coach/CoachHomeScreen.js
echo "sintaxis exit=$?"
npm run verificar-iconos
```

Esperado: seis `OK`, `sintaxis exit=0`, y `OK: 16 iconos válidos`.

- [ ] **Step 2: Comprobación cruzada final de nombres de icono**

Repite el script de `node -e` del Step 5 de la Task 2. Esperado: `OK: todos los nombres de icono existen`.

- [ ] **Step 3: Confirmar que no se tocó el backend**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol
git diff --name-only main...HEAD | grep -E '^(api|web)/' ; echo "coincidencias: $?"
```

Esperado: sin salida y `coincidencias: 1`. Fíate de que **no haya salida de texto**, no del código de `git diff`. Si aparece algo, **para**: el spec prohíbe tocar `api/` y `web/`.

- [ ] **Step 4: Suite de Python**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol/api && .venv/bin/python -m pytest -q 2>&1 | tail -5
```

Esperado: `233 passed`. **Tarda ~12,5 minutos**: córrela **en primer plano** con un timeout de 900000 ms y espera a que acabe. No la lances en segundo plano esperando una notificación — no llega. Si el número no es 233, repórtalo tal cual sin maquillarlo.

- [ ] **Step 5: Escribir el checklist**

Crea `docs/superpowers/checklist-iconos-navegacion.md`:

```markdown
# Checklist de validación en dispositivo — iconos de navegación y pantallas

Lo estático ya está verificado: los archivos tocados parsean, los 16 iconos pasan
sus aserciones, todo `nombre=` usado existe en el catálogo, y los 233 tests de
Python siguen en verde.

**Lo que esto busca:** una errata en un nombre de icono no da error, da un hueco
invisible. La comprobación cruzada descarta nombres inexistentes, pero no que un
icono esté puesto en la pestaña equivocada. Por eso hay que mirar las cuatro barras.

## Preparación
1. Backend arriba: `docker compose up -d`.
2. `cd mobile && npx expo start` (modo LAN, **sin** `--tunnel`) y escanea el QR con
   Expo Go. En modo LAN la IP de la API se deriva sola; no toques `app.json`.
3. Si tras instalar iconos nuevos el bundle falla, arranca con `npx expo start -c`.

## 1. Barra de navegación — los cuatro roles
- [ ] **Sin sesión** (pública): dos pestañas, INICIO con una **casa** y TORNEOS con
      una **copa**. La activa en verde, la otra en gris.
- [ ] **Jugador** (jugador@demo.com / demo1234): INICIO casa, TORNEOS copa,
      RESERVAR CANCHA **calendario**, MI PERFIL **persona**.
- [ ] **Entrenador** (entrenador@demo.com / demo1234): INICIO casa, MIS EQUIPOS
      **gente**, TORNEOS copa, PERFIL persona.
- [ ] **Árbitro** (arbitro@demo.com / demo1234): PARTIDOS ASIGNADOS **balón**,
      HISTORIAL **reloj/historial**, PERFIL persona.
- [ ] Ninguna pestaña muestra un hueco vacío donde debería ir su icono.
- [ ] El puntito gris de antes ya no aparece en ninguna barra.
- [ ] La barra no se ve desproporcionadamente alta ni recorta las etiquetas.

## 2. Pantallas
- [ ] **TORNEOS** (cualquier rol): cada torneo de la lista lleva una **copa** dentro
      del círculo verde, no un emoji.
- [ ] **INICIO del jugador**: "Ver mis estadísticas" con un **gráfico** blanco, y
      "Próximos partidos" con un **calendario** verde. Icono y texto en la misma
      línea, centrados, sin que el texto se parta.
- [ ] **RESERVAR CANCHA**: el buscador muestra un **marcador de mapa** a la
      izquierda y el texto gris "Buscar sede". Al escribir, el texto no se monta
      sobre el icono y el filtrado de sedes sigue funcionando.
- [ ] **INICIO del entrenador**: la rejilla muestra gente / documento con "+" /
      portapapeles con lista / calendario, en ese orden. "Inscribir" y "Reservar"
      siguen avisando "Disponible próximamente".

## Si algo falla
Anota **rol, pantalla y qué viste** (o captura). Lo más probable:
1. Hueco vacío donde va un icono → nombre mal escrito; comprueba la clave contra
   `mobile/src/components/iconos-datos.json`.
2. Icono correcto pero en la pestaña equivocada → revisa `tabBarIcon` en `App.js`.
3. Icono incompleto o deformado → falta un path; vuelve a generar con
   `node scripts/generar-iconos.cjs`.
4. "Unable to resolve module" → caché de Metro; `npx expo start -c`.
```

- [ ] **Step 6: Commitear el checklist**

```bash
git add docs/superpowers/checklist-iconos-navegacion.md
git commit -m "docs(movil): checklist de validacion de iconos de navegacion"
```

---

## Auto-revisión del plan

**Cobertura del spec:**

| Requisito del spec | Tarea |
|---|---|
| Catálogo de 5 a 16 iconos | Task 1 |
| `location` de Reicon `Pin`, no del macro web | Task 1, Step 2 (`DESDE_REICON`) |
| Reicon solo a scratchpad, nunca en `package.json` | Task 1, Step 1 + Global Constraints |
| `verificar-iconos.cjs` ampliado a 16 | Task 1, Step 5 |
| `Icono.js` no cambia | Global Constraints (ninguna tarea lo toca) |
| El icono sustituye al punto; etiquetas se conservan | Task 2, Steps 2-3 |
| `size={22}` en la barra | Task 2, Step 3 |
| Asignación por pestaña (7 combinaciones) | Task 2, Step 3 |
| `🏆` de TorneosScreen | Task 3, Step 1 |
| `📊` y `📅` de PlayerHomeScreen, botones en fila | Task 3, Step 2 |
| Rejilla del entrenador (4 iconos) | Task 3, Step 3 |
| `📍` fuera del `placeholder`, buscador en fila | Task 4 |
| Sin cambios en `api/` ni `web/` | Task 5, Step 3 (comprobación activa) |
| Suite Python en 233 | Task 5, Step 4 |
| Validación en dispositivo con checklist | Task 5, Steps 5-6 |
| Fuera de alcance: NotificationsScreen, HomeScreen, eventos, `✓`/`✕`/`📎` | Ninguna tarea los toca |

Sin huecos.

**Consistencia de nombres** (verificada entre tareas): las 11 claves nuevas se escriben igual en el generador (Task 1), en `ESPERADOS` (Task 1 Step 5), en los `tabBarIcon` (Task 2) y en las pantallas (Tasks 3-4): `cuptrophy`, `chart`, `calendar`, `people`, `football`, `home`, `user`, `history`, `clipboardlist`, `docadd`, `location`. La comprobación cruzada de las Tasks 2, 3 y 5 las valida contra el JSON de forma automática, así que una discrepancia no puede sobrevivir a la ejecución.

**Decisión de diseño del plan, no del spec:** el spec no dice cómo llevar los paths al JSON. El plan usa un **generador** en vez de transcripción manual porque `calendar` (7 paths) y `people` (6) son largos y perder uno da un icono incompleto sin error. El Step 3 de la Task 1 valida los recuentos contra la tabla del spec, así que una fuente que cambie se detecta en vez de colarse.

**Riesgo conocido, sin mitigar en el plan:** el Step 1 de la Task 1 depende de `npm pack reicon@1.1.103` (red). Si falla, la tarea queda bloqueada; no hay copia de los paths en el repo. Es el mismo patrón de los PRs #18 y #21, aceptado allí.
