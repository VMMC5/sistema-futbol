# Iconos vectoriales y menú de perfil unificado (móvil) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sustituir los emojis del menú de perfil y de la campanita por SVG de Reicon renderizados con `react-native-svg`, y llevar ese mismo menú a entrenador y árbitro.

**Architecture:** Un componente `Icono` (espejo del macro `icono()` de la web) alimentado por un módulo de datos puro; tres piezas compartidas (fila de menú, modal de edición, hook de foto) que eliminan la duplicación entre las dos pantallas de perfil; y la reescritura de ambas pantallas para consumirlas.

**Tech Stack:** React Native 0.74.5 / Expo SDK 51, `react-native-svg` 15.2.0, `@react-navigation`. Sin backend.

**Spec:** `docs/superpowers/specs/2026-07-27-iconos-y-menu-de-perfil-movil-design.md`

## Global Constraints

- **Dependencia nueva:** `react-native-svg` `~15.2.0`, instalada **solo** con `npx expo install react-native-svg` (fija la versión del SDK 51). No usar `npm install` a secas.
- **`viewBox` siempre `0 0 24 24`**, en todos los iconos, sea cual sea el `size`.
- El paquete `reicon` se descarga **solo a scratchpad**, nunca a `node_modules` del proyecto ni a `package.json`. Los paths se copian a mano al código. Directorio de scratchpad de esta sesión: `/tmp/claude-1000/-home-vikca-sistema-torneos-sistema-futbol/b78e92d0-83bc-43e4-91b1-c544edefb325/scratchpad`
- **No se toca `api/` ni `web/`.** La suite de Python debe seguir en **233 en verde** al final; cualquier cambio en esos directorios es una señal de alarma.
- **No hay runner de tests JS.** La verificación por tarea es `node scripts/verificar-sintaxis.cjs <archivos…>` (creado en la Task 1) más, para los datos de iconos, `node scripts/verificar-iconos.cjs`.
- **No uses `npx babel`.** Resuelve al paquete `babel` v6 **deprecado** del caché de npx (`~/.npm/_npx/…/node_modules/babel/`), no a `@babel/cli`, y da resultados inconsistentes: se comprobó que hace fallar archivos válidos. `@babel/core` sí está en `mobile/node_modules`, y el verificador de la Task 1 lo usa directamente. *(La nota "3/3 babel OK" del ledger del PR #20 se apoyaba en ese comando; su valor era dudoso.)*
- **Idioma:** comentarios, nombres de variables y textos de UI en español, como el resto de `mobile/src/`.
- **Rama:** `feat/iconos-perfil-movil`, ya creada. El spec ya está commiteado en `879e84a`.

### Refinamiento respecto al spec

El spec describe un único `src/components/Icono.js` con el dict `ICONOS` dentro. El plan lo parte en dos:

- `src/components/iconos-datos.json` — los 5 iconos como datos puros, **en JSON**.
- `src/components/Icono.js` — el componente, que importa ese JSON.

**Motivo:** el módulo de datos se puede validar con `node` sin emulador ni runner de tests. Dado que el proyecto no tiene tests JS, esto convierte la parte más propensa a erratas (copiar paths SVG a mano) en algo verificable de verdad. El contrato público del spec (`<Icono nombre size color />`) no cambia.

**Por qué JSON y no un `.js` con `export default`:** `mobile/package.json` no declara `"type": "module"`, así que Node trata los `.js` como CommonJS y un `export default` solo se carga por la autodetección de sintaxis de Node ≥ 22.7 — y con warning. El verificador dejaría de funcionar en cualquier Node anterior. JSON lo lee `require()` sin transpilar y Metro lo importa de forma nativa; ambas cosas verificadas en este repo. El coste es que JSON no admite comentarios: la documentación del formato vive en la cabecera de `Icono.js`.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `mobile/src/components/iconos-datos.json` | **Crear.** Los 5 iconos como datos puros. Sin dependencias. |
| `mobile/src/components/Icono.js` | **Crear.** Renderiza un icono con `react-native-svg`. |
| `mobile/scripts/verificar-sintaxis.cjs` | **Crear.** Parseo con el `@babel/core` del proyecto. |
| `mobile/scripts/verificar-iconos.cjs` | **Crear.** Aserciones sobre los datos de iconos. |
| `mobile/src/components/OpcionMenu.js` | **Crear.** Fila de menú (icono · texto · chevron). |
| `mobile/src/components/EditarPerfilModal.js` | **Crear.** Modal de nombre/teléfono contra `PUT /auth/me`. |
| `mobile/src/hooks/useFotoPerfil.js` | **Crear.** Lógica de subir/quitar foto, hoy duplicada. |
| `mobile/src/screens/player/PlayerProfileScreen.js` | **Modificar.** Consume las piezas compartidas; emojis → `<Icono>`. |
| `mobile/src/screens/PerfilScreen.js` | **Mover** desde `screens/coach/` y reescribir. |
| `mobile/src/screens/player/PlayerHomeScreen.js` | **Modificar.** Campanita `🔔` → `<Icono nombre="bell">`. |
| `mobile/App.js` | **Modificar.** Ruta del import de `PerfilScreen`. |
| `mobile/package.json` | **Modificar.** Entra `react-native-svg`. |

---

## Task 1: Sistema de iconos

**Files:**
- Create: `mobile/scripts/verificar-sintaxis.cjs`
- Create: `mobile/scripts/verificar-iconos.cjs`
- Create: `mobile/src/components/iconos-datos.json`
- Create: `mobile/src/components/Icono.js`
- Modify: `mobile/package.json` (vía `npx expo install`)

**Interfaces:**
- Produces: `iconos-datos.json` — objeto cuyas claves son `edit`, `creditcard`, `lock`, `logout`, `bell`. Cada valor es `{ d: string[], trazo?: boolean, parImpar?: boolean }`.
- Produces: `Icono` (export por defecto de `Icono.js`) — componente con props `{ nombre: string, size?: number, color?: string }`. `size` por defecto `18`, `color` por defecto `lp.textDark`.
- Produces: `scripts/verificar-sintaxis.cjs` — se invoca con rutas de archivo como argumentos; sale 0 si todas parsean, 1 si alguna falla. Lo usan todas las tareas siguientes.

- [ ] **Step 1: Instalar la dependencia**

```bash
cd mobile && npx expo install react-native-svg
```

Comprueba que quedó la versión correcta:

```bash
cd mobile && grep react-native-svg package.json
```

Esperado: `"react-native-svg": "15.2.0"` (o `~15.2.0`). Si `expo install` propone otra versión, **para y avisa** — significa que el SDK no es el 51.

- [ ] **Step 2: Crear el verificador de sintaxis**

Crea `mobile/scripts/verificar-sintaxis.cjs`. Usa el `@babel/core` que ya está en `node_modules`; **no** uses `npx babel` (ver Global Constraints):

```js
// Parseo de sintaxis con el @babel/core del proyecto.
// Uso: node scripts/verificar-sintaxis.cjs App.js src/components/Icono.js ...
const path = require("path");
const babel = require(path.join(process.cwd(), "node_modules", "@babel", "core"));

let malos = 0;
for (const archivo of process.argv.slice(2)) {
  try {
    babel.transformFileSync(archivo, {
      presets: ["babel-preset-expo"],
      babelrc: false,
      configFile: false,
    });
    console.log("OK    " + archivo);
  } catch (e) {
    console.log("FALLO " + archivo + " -> " + e.message.split("\n")[0]);
    malos++;
  }
}
process.exit(malos ? 1 : 0);
```

- [ ] **Step 3: Comprobar que el verificador detecta un archivo roto**

Sin esta comprobación no sabes si el verificador sirve de algo:

```bash
cd mobile
printf 'export default function Roto( {\n  const x = ;;;\n' > _roto.js
node scripts/verificar-sintaxis.cjs App.js _roto.js; echo "exit=$?"
rm -f _roto.js
```

Esperado: `OK    App.js`, luego `FALLO _roto.js -> ... Unexpected keyword 'const'`, y `exit=1`. Si el roto sale `OK`, **para**: el verificador no está validando nada.

- [ ] **Step 4: Escribir el verificador de iconos (falla primero)**

Crea `mobile/scripts/verificar-iconos.cjs`:

```js
// Valida los datos de iconos sin React Native ni emulador.
// Uso: node scripts/verificar-iconos.cjs
const ICONOS = require("../src/components/iconos-datos.json");

const ESPERADOS = ["edit", "creditcard", "lock", "logout", "bell"];
const fallos = [];

for (const nombre of ESPERADOS) {
  const def = ICONOS[nombre];
  if (!def) { fallos.push(`falta el icono "${nombre}"`); continue; }
  if (!Array.isArray(def.d) || def.d.length === 0) {
    fallos.push(`"${nombre}": "d" debe ser un array no vacío`);
    continue;
  }
  def.d.forEach((d, i) => {
    if (typeof d !== "string" || !d.trim().startsWith("M")) {
      fallos.push(`"${nombre}"[${i}]: un path SVG debe empezar por "M"`);
    }
    if (/#[0-9a-fA-F]{3,6}/.test(d)) {
      fallos.push(`"${nombre}"[${i}]: color literal incrustado; el color va por prop`);
    }
  });
}

const sobran = Object.keys(ICONOS).filter((k) => !ESPERADOS.includes(k));
if (sobran.length) fallos.push(`iconos no esperados: ${sobran.join(", ")}`);

if (fallos.length) {
  console.error("FALLO:\n" + fallos.map((f) => "  - " + f).join("\n"));
  process.exit(1);
}
console.log(`OK: ${ESPERADOS.length} iconos válidos`);
```

- [ ] **Step 5: Ejecutarlo para verificar que falla**

```bash
cd mobile && node scripts/verificar-iconos.cjs
```

Esperado: FALLA con `Cannot find module '../src/components/iconos-datos.json'`.

- [ ] **Step 6: Crear el módulo de datos**

Crea `mobile/src/components/iconos-datos.json`. Los paths están copiados de Reicon (reicon.dev, MIT) — `edit` de `Edit2`, `lock` de `Lock`, `logout` de `Logout`, `bell` de `Bell`; `creditcard` viene del macro `web/app/templates/_iconos.html`, para que móvil y web pinten exactamente la misma tarjeta. El significado de `trazo` y `parImpar` está documentado en la cabecera de `Icono.js` (JSON no admite comentarios).

```json
{
  "edit": {
    "trazo": true,
    "d": [
      "M13.26 3.59997L5.04997 12.29C4.73997 12.62 4.43997 13.27 4.37997 13.72L4.00997 16.96C3.87997 18.13 4.71997 18.93 5.87997 18.73L9.09997 18.18C9.54997 18.1 10.18 17.77 10.49 17.43L18.7 8.73997C20.12 7.23997 20.76 5.52997 18.55 3.43997C16.35 1.36997 14.68 2.09997 13.26 3.59997Z",
      "M11.89 5.05005C12.32 7.81005 14.56 9.92005 17.34 10.2",
      "M3 22H21"
    ]
  },
  "creditcard": {
    "parImpar": true,
    "d": [
      "M10 14.75C10.4142 14.75 10.75 15.0858 10.75 15.5C10.75 15.9142 10.4142 16.25 10 16.25H5.5C5.08579 16.25 4.75 15.9142 4.75 15.5C4.75 15.0858 5.08579 14.75 5.5 14.75H10Z",
      "M15.25 15.5C15.25 15.9142 14.9142 16.25 14.5 16.25H13C12.5858 16.25 12.25 15.9142 12.25 15.5C12.25 15.0858 12.5858 14.75 13 14.75H14.5C14.9142 14.75 15.25 15.0858 15.25 15.5Z",
      "M17.7321 3.25H6.2679C5.45506 3.24999 4.79944 3.24999 4.26853 3.29336C3.7219 3.33803 3.24175 3.43239 2.79754 3.65873C2.09193 4.01825 1.51825 4.59193 1.15873 5.29754C0.932386 5.74175 0.838026 6.2219 0.793364 6.76853C0.749987 7.29944 0.749993 7.95505 0.75 8.76788V15.2321C0.749993 16.0449 0.749987 16.7006 0.793364 17.2315C0.838026 17.7781 0.932386 18.2582 1.15873 18.7025C1.51825 19.4081 2.09193 19.9818 2.79754 20.3413C3.24175 20.5676 3.7219 20.662 4.26853 20.7066C4.79944 20.75 5.45505 20.75 6.26788 20.75H17.7321C18.545 20.75 19.2006 20.75 19.7315 20.7066C20.2781 20.662 20.7582 20.5676 21.2025 20.3413C21.9081 19.9818 22.4817 19.4081 22.8413 18.7025C23.0676 18.2582 23.162 17.7781 23.2066 17.2315C23.25 16.7005 23.25 16.0449 23.25 15.232V8.76798C23.25 7.9551 23.25 7.29946 23.2066 6.76853C23.162 6.2219 23.0676 5.74175 22.8413 5.29754C22.4817 4.59193 21.9081 4.01825 21.2025 3.65873C20.7582 3.43239 20.2781 3.33803 19.7315 3.29336C19.2006 3.24999 18.5449 3.24999 17.7321 3.25ZM21.75 8.75C21.75 7.92422 21.7487 7.34421 21.7116 6.89068C21.6745 6.43681 21.6054 6.17604 21.5048 5.97852C21.289 5.55516 20.9448 5.21095 20.5215 4.99524C20.324 4.8946 20.0632 4.82547 19.6093 4.78838C19.1467 4.75058 18.5525 4.75 17.7 4.75H6.3C5.44755 4.75 4.85331 4.75058 4.39068 4.78838C3.93681 4.82547 3.67604 4.8946 3.47852 4.99524C3.05516 5.21095 2.71095 5.55516 2.49524 5.97852C2.3946 6.17604 2.32547 6.43681 2.28838 6.89068C2.25133 7.34421 2.25004 7.92422 2.25 8.75H21.75ZM2.25 10.25H21.75V15.2C21.75 16.0525 21.7494 16.6467 21.7116 17.1093C21.6745 17.5632 21.6054 17.824 21.5048 18.0215C21.289 18.4448 20.9448 18.7891 20.5215 19.0048C20.324 19.1054 20.0632 19.1745 19.6093 19.2116C19.1467 19.2494 18.5525 19.25 17.7 19.25H6.3C5.44755 19.25 4.85331 19.2494 4.39068 19.2116C3.93681 19.1745 3.67604 19.1054 3.47852 19.0048C3.05516 18.7891 2.71095 18.4448 2.49524 18.0215C2.3946 17.824 2.32547 17.5632 2.28838 17.1093C2.25058 16.6467 2.25 16.0525 2.25 15.2V10.25Z"
    ]
  },
  "lock": {
    "parImpar": true,
    "d": [
      "M5.25 9.30277V8C5.25 4.27208 8.27208 1.25 12 1.25C15.7279 1.25 18.75 4.27208 18.75 8V9.30277C18.9768 9.31872 19.1906 9.33948 19.3918 9.36652C20.2919 9.48754 21.0497 9.74643 21.6517 10.3483C22.2536 10.9503 22.5125 11.7081 22.6335 12.6082C22.75 13.4752 22.75 14.5775 22.75 15.9451V16.0549C22.75 17.4225 22.75 18.5248 22.6335 19.3918C22.5125 20.2919 22.2536 21.0497 21.6517 21.6516C21.0497 22.2536 20.2919 22.5125 19.3918 22.6335C18.5248 22.75 17.4225 22.75 16.0549 22.75H7.94513C6.57754 22.75 5.47522 22.75 4.60825 22.6335C3.70814 22.5125 2.95027 22.2536 2.34835 21.6516C1.74643 21.0497 1.48754 20.2919 1.36652 19.3918C1.24996 18.5248 1.24998 17.4225 1.25 16.0549V15.9451C1.24998 14.5775 1.24996 13.4752 1.36652 12.6082C1.48754 11.7081 1.74643 10.9503 2.34835 10.3483C2.95027 9.74643 3.70814 9.48754 4.60825 9.36652C4.80938 9.33948 5.02317 9.31872 5.25 9.30277ZM6.75 8C6.75 5.10051 9.10051 2.75 12 2.75C14.8995 2.75 17.25 5.10051 17.25 8V9.25344C16.8765 9.24999 16.4784 9.24999 16.0549 9.25H7.94513C7.52161 9.24999 7.12353 9.24999 6.75 9.25344V8ZM3.40901 11.409C3.68577 11.1322 4.07435 10.9518 4.80812 10.8531C5.56347 10.7516 6.56459 10.75 8 10.75H16C17.4354 10.75 18.4365 10.7516 19.1919 10.8531C19.9257 10.9518 20.3142 11.1322 20.591 11.409C20.8678 11.6858 21.0482 12.0743 21.1469 12.8081C21.2484 13.5635 21.25 14.5646 21.25 16C21.25 17.4354 21.2484 18.4365 21.1469 19.1919C21.0482 19.9257 20.8678 20.3142 20.591 20.591C20.3142 20.8678 19.9257 21.0482 19.1919 21.1469C18.4365 21.2484 17.4354 21.25 16 21.25H8C6.56459 21.25 5.56347 21.2484 4.80812 21.1469C4.07435 21.0482 3.68577 20.8678 3.40901 20.591C3.13225 20.3142 2.9518 19.9257 2.85315 19.1919C2.75159 18.4365 2.75 17.4354 2.75 16C2.75 14.5646 2.75159 13.5635 2.85315 12.8081C2.9518 12.0743 3.13225 11.6858 3.40901 11.409Z"
    ]
  },
  "logout": {
    "d": [
      "M12 3.25C12.4142 3.25 12.75 3.58579 12.75 4C12.75 4.41421 12.4142 4.75 12 4.75C7.99594 4.75 4.75 7.99594 4.75 12C4.75 16.0041 7.99594 19.25 12 19.25C12.4142 19.25 12.75 19.5858 12.75 20C12.75 20.4142 12.4142 20.75 12 20.75C7.16751 20.75 3.25 16.8325 3.25 12C3.25 7.16751 7.16751 3.25 12 3.25Z",
      "M16.4697 9.53033C16.1768 9.23744 16.1768 8.76256 16.4697 8.46967C16.7626 8.17678 17.2374 8.17678 17.5303 8.46967L20.5303 11.4697C20.8232 11.7626 20.8232 12.2374 20.5303 12.5303L17.5303 15.5303C17.2374 15.8232 16.7626 15.8232 16.4697 15.5303C16.1768 15.2374 16.1768 14.7626 16.4697 14.4697L18.1893 12.75H10C9.58579 12.75 9.25 12.4142 9.25 12C9.25 11.5858 9.58579 11.25 10 11.25H18.1893L16.4697 9.53033Z"
    ]
  },
  "bell": {
    "parImpar": true,
    "d": [
      "M12 1.25C7.71983 1.25 4.25004 4.71979 4.25004 9V9.7041C4.25004 10.401 4.04375 11.0824 3.65717 11.6622L2.50856 13.3851C1.17547 15.3848 2.19318 18.1028 4.51177 18.7351C5.26738 18.9412 6.02937 19.1155 6.79578 19.2581L6.79768 19.2632C7.56667 21.3151 9.62198 22.75 12 22.75C14.378 22.75 16.4333 21.3151 17.2023 19.2632L17.2042 19.2581C17.9706 19.1155 18.7327 18.9412 19.4883 18.7351C21.8069 18.1028 22.8246 15.3848 21.4915 13.3851L20.3429 11.6622C19.9563 11.0824 19.75 10.401 19.75 9.7041V9C19.75 4.71979 16.2802 1.25 12 1.25ZM15.3764 19.537C13.1335 19.805 10.8664 19.8049 8.62349 19.5369C9.33444 20.5585 10.571 21.25 12 21.25C13.4289 21.25 14.6655 20.5585 15.3764 19.537ZM5.75004 9C5.75004 5.54822 8.54826 2.75 12 2.75C15.4518 2.75 18.25 5.54822 18.25 9V9.7041C18.25 10.6972 18.544 11.668 19.0948 12.4943L20.2434 14.2172C21.0086 15.3649 20.4245 16.925 19.0936 17.288C14.4494 18.5546 9.5507 18.5546 4.90644 17.288C3.57561 16.925 2.99147 15.3649 3.75664 14.2172L4.90524 12.4943C5.45609 11.668 5.75004 10.6972 5.75004 9.7041V9Z"
    ]
  }
}
```

- [ ] **Step 7: Ejecutar el verificador de iconos**

```bash
cd mobile && node scripts/verificar-iconos.cjs
```

Esperado: `OK: 5 iconos válidos`

- [ ] **Step 8: Crear el componente**

Crea `mobile/src/components/Icono.js`:

```js
// Icono vectorial. Espejo del macro icono() de la web: mismos paths de Reicon
// (reicon.dev, MIT), mismo viewBox 0 0 24 24. El color llega por prop, como
// currentColor en la web.
//
// Formato de cada entrada de iconos-datos.json (el JSON no admite comentarios):
//   d         paths del icono, en orden de pintado
//   trazo     true -> se pintan con stroke y fill none; ausente -> con fill
//   parImpar  true -> fillRule/clipRule "evenodd" (el icono lo declara en su SVG)
import React from "react";
import Svg, { Path } from "react-native-svg";
import ICONOS from "./iconos-datos.json";
import { lp } from "../publicTheme";

export default function Icono({ nombre, size = 18, color = lp.textDark }) {
  const def = ICONOS[nombre];
  // Un nombre desconocido pinta un hueco del tamaño pedido, nunca revienta
  // (mismo criterio que _REICON.get(nombre, "") en la plantilla web).
  const paths = def?.d || [];
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {paths.map((d, i) =>
        def.trazo ? (
          <Path
            key={i}
            d={d}
            stroke={color}
            strokeWidth={1.5}
            strokeMiterlimit={10}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        ) : (
          <Path
            key={i}
            d={d}
            fill={color}
            fillRule={def.parImpar ? "evenodd" : "nonzero"}
            clipRule={def.parImpar ? "evenodd" : "nonzero"}
          />
        ),
      )}
    </Svg>
  );
}
```

- [ ] **Step 9: Verificar la sintaxis**

```bash
cd mobile && node scripts/verificar-sintaxis.cjs src/components/Icono.js
```

Esperado: `OK    src/components/Icono.js`

- [ ] **Step 10: Commit**

```bash
git add mobile/package.json mobile/package-lock.json \
  mobile/src/components/iconos-datos.json mobile/src/components/Icono.js \
  mobile/scripts/verificar-sintaxis.cjs mobile/scripts/verificar-iconos.cjs
git commit -m "feat(movil): componente Icono con SVG de Reicon"
```

---

## Task 2: Piezas compartidas de perfil

`PlayerProfileScreen` y `PerfilScreen` duplican hoy la lógica de foto y no comparten ni la fila de menú ni el modal de edición. Se extraen las tres piezas antes de reescribir las pantallas.

**Files:**
- Create: `mobile/src/components/OpcionMenu.js`
- Create: `mobile/src/hooks/useFotoPerfil.js`
- Create: `mobile/src/components/EditarPerfilModal.js`

**Interfaces:**
- Consumes: `Icono` de Task 1.
- Produces: `OpcionMenu` (default) — props `{ icono: string, texto: string, onPress: () => void, color?: string }`.
- Produces: `useFotoPerfil` (default) — hook sin argumentos. Devuelve `{ subiendo: boolean, fotoV: number, cambiarFoto: () => Promise<void>, quitarFoto: () => void }`. `fotoV` se pasa tal cual al prop `version` de `Avatar`.
- Produces: `EditarPerfilModal` (default) — props `{ visible: boolean, nombreInicial: string, telefonoInicial: string, acento?: string, onCerrar: () => void, onGuardado: (usuarioActualizado) => void }`.

- [ ] **Step 1: Crear la fila de menú**

Crea `mobile/src/components/OpcionMenu.js`. Es la función `Opcion` que hoy vive al final de `PlayerProfileScreen.js`, con el emoji sustituido por `<Icono>`:

```js
// Fila de menú de las pantallas de perfil: icono, texto y chevron.
import React from "react";
import { Text, TouchableOpacity } from "react-native";
import Icono from "./Icono";
import { lp, ls } from "../publicTheme";

export default function OpcionMenu({ icono, texto, onPress, color }) {
  const tinte = color || lp.textDark;
  return (
    <TouchableOpacity style={[ls.row, { alignItems: "center" }]} onPress={onPress}>
      <Icono nombre={icono} size={18} color={tinte} />
      <Text style={{ flex: 1, fontWeight: "700", color: tinte, marginLeft: 12 }}>{texto}</Text>
      <Text style={{ color: lp.textMuted, fontSize: 20 }}>›</Text>
    </TouchableOpacity>
  );
}
```

- [ ] **Step 2: Crear el hook de foto**

Crea `mobile/src/hooks/useFotoPerfil.js`. Es la lógica de `PlayerProfileScreen.js:53-98`, sin cambios de comportamiento:

```js
// Subir y quitar la foto de perfil. Devuelve fotoV, que sube en cada cambio
// para que <Avatar version={fotoV}> descarte su caché (fix del PR #20).
import { useState } from "react";
import { Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { borrarFoto, subirFoto } from "../api";
import { useAuth } from "../auth";

export default function useFotoPerfil() {
  const { refrescar } = useAuth();
  const [subiendo, setSubiendo] = useState(false);
  const [fotoV, setFotoV] = useState(0);

  async function cambiarFoto() {
    const permiso = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permiso.granted) {
      Alert.alert("Permiso necesario", "Habilita el acceso a tus fotos para cambiar la imagen de perfil.");
      return;
    }
    const resultado = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (resultado.canceled) return;
    setSubiendo(true);
    try {
      await subirFoto(resultado.assets[0].uri);
      await refrescar();
      setFotoV((v) => v + 1);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo subir la foto");
    } finally {
      setSubiendo(false);
    }
  }

  function quitarFoto() {
    Alert.alert("Quitar foto", "¿Quitar tu foto de perfil?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Quitar",
        style: "destructive",
        onPress: async () => {
          setSubiendo(true);
          try {
            await borrarFoto();
            await refrescar();
            setFotoV((v) => v + 1);
          } catch (e) {
            Alert.alert("Error", e.message || "No se pudo quitar la foto");
          } finally {
            setSubiendo(false);
          }
        },
      },
    ]);
  }

  return { subiendo, fotoV, cambiarFoto, quitarFoto };
}
```

- [ ] **Step 3: Crear el modal de edición**

Crea `mobile/src/components/EditarPerfilModal.js`. Es el modal de `PlayerProfileScreen.js:146-162` más su función `guardar` (líneas 38-51), con el `PUT /auth/me` dentro:

```js
// Modal de "Editar datos personales" (nombre y teléfono) contra PUT /auth/me.
// Los valores iniciales llegan por props: useAuth().usuario ya trae ambos, así
// que el modal no pide nada al abrirse.
import React, { useEffect, useState } from "react";
import { Alert, Modal, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiPut } from "../api";
import { useAuth } from "../auth";
import { lp } from "../publicTheme";

export default function EditarPerfilModal({
  visible, nombreInicial, telefonoInicial, acento = lp.accent, onCerrar, onGuardado,
}) {
  const { refrescar } = useAuth();
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [guardando, setGuardando] = useState(false);

  // Al abrirse, parte siempre de los valores actuales.
  useEffect(() => {
    if (visible) {
      setNombre(nombreInicial || "");
      setTelefono(telefonoInicial || "");
    }
  }, [visible, nombreInicial, telefonoInicial]);

  async function guardar() {
    if (nombre.trim().length < 2) {
      Alert.alert("Nombre inválido", "Escribe tu nombre completo.");
      return;
    }
    setGuardando(true);
    try {
      const actualizado = await apiPut("/auth/me", { nombre: nombre.trim(), telefono: telefono.trim() });
      await refrescar();
      onGuardado?.(actualizado);
      onCerrar();
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCerrar}>
      <View style={estilos.fondo}>
        <View style={estilos.panel}>
          <Text style={estilos.titulo}>Editar datos personales</Text>
          <Text style={estilos.campoLbl}>Nombre</Text>
          <TextInput
            style={estilos.input} value={nombre} onChangeText={setNombre}
            placeholder="Tu nombre" placeholderTextColor={lp.textMuted}
          />
          <Text style={[estilos.campoLbl, { marginTop: 10 }]}>Teléfono</Text>
          <TextInput
            style={estilos.input} value={telefono} onChangeText={setTelefono}
            keyboardType="phone-pad" placeholder="Opcional" placeholderTextColor={lp.textMuted}
          />
          <TouchableOpacity
            style={[estilos.guardarBtn, { backgroundColor: acento }, guardando && { opacity: 0.6 }]}
            onPress={guardar} disabled={guardando}
          >
            <Text style={{ color: lp.white, fontWeight: "800" }}>{guardando ? "Guardando..." : "Guardar"}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={{ paddingVertical: 12, alignItems: "center" }} onPress={onCerrar}>
            <Text style={{ color: lp.textMuted, fontWeight: "700" }}>Cancelar</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const estilos = {
  fondo: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "center", padding: 24 },
  panel: { backgroundColor: lp.bg, borderRadius: 16, padding: 20 },
  titulo: { color: lp.textDark, fontWeight: "800", fontSize: 17, marginBottom: 14 },
  campoLbl: { color: lp.textMuted, fontWeight: "700", marginBottom: 6 },
  input: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, color: lp.textDark, paddingHorizontal: 14, paddingVertical: 12 },
  guardarBtn: { borderRadius: 10, paddingVertical: 14, alignItems: "center", marginTop: 16 },
};
```

- [ ] **Step 4: Verificar la sintaxis de los tres**

```bash
cd mobile && node scripts/verificar-sintaxis.cjs \
  src/components/OpcionMenu.js src/hooks/useFotoPerfil.js src/components/EditarPerfilModal.js
```

Esperado: tres líneas `OK` y exit 0.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/components/OpcionMenu.js mobile/src/hooks/useFotoPerfil.js mobile/src/components/EditarPerfilModal.js
git commit -m "refactor(movil): extrae fila de menu, modal de edicion y hook de foto"
```

---

## Task 3: Perfil del jugador consume las piezas compartidas

**Files:**
- Modify: `mobile/src/screens/player/PlayerProfileScreen.js`

**Interfaces:**
- Consumes: `Icono`, `OpcionMenu`, `useFotoPerfil`, `EditarPerfilModal` de Tasks 1-2.
- Produces: nada que consuman otras tareas.

El layout, las cajas GOLES/PARTIDOS y el comportamiento **no cambian**. Solo cambia de dónde viene el código.

- [ ] **Step 1: Reescribir el archivo**

Sustituye el contenido completo de `mobile/src/screens/player/PlayerProfileScreen.js` por:

```js
// MI PERFIL: avatar (foto o iniciales), datos, cajas de stats y accesos a
// editar datos personales, métodos de pago (próximamente), contraseña y
// cerrar sesión.
import React, { useCallback, useState } from "react";
import { useFocusEffect, CommonActions } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import Avatar from "../../components/Avatar";
import EditarPerfilModal from "../../components/EditarPerfilModal";
import OpcionMenu from "../../components/OpcionMenu";
import useFotoPerfil from "../../hooks/useFotoPerfil";
import { apiGet } from "../../api";
import { useAuth } from "../../auth";
import { lp, ls } from "../../publicTheme";

export default function PlayerProfileScreen({ navigation }) {
  const { usuario, logout } = useAuth();
  const [stats, setStats] = useState({ goles: 0, partidos: 0 });
  const [me, setMe] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [editar, setEditar] = useState(false);
  const { subiendo, fotoV, cambiarFoto, quitarFoto } = useFotoPerfil();

  const cargar = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([apiGet("/auth/me"), apiGet("/jugador/estadisticas")]);
      setMe(m); setStats(s);
    } catch (_) {} finally { setCargando(false); }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function cerrarSesion() {
    await logout();
    navigation.dispatch(CommonActions.reset({ index: 0, routes: [{ name: "Public" }] }));
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.green} style={{ marginTop: 40 }} /></View>;
  }

  const nombreMostrar = me?.nombre || usuario?.nombre || "Jugador";

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Encabezado */}
      <View style={{ alignItems: "center", marginVertical: 12 }}>
        <Avatar usuarioId={me?.id || usuario?.id} nombre={nombreMostrar} size={72} version={fotoV} />
        <Text style={{ color: lp.textDark, fontSize: 20, fontWeight: "800", marginTop: 12 }}>{nombreMostrar}</Text>
        <Text style={[ls.badge, { backgroundColor: lp.surface, color: lp.green, borderWidth: 1, borderColor: lp.surfaceBorder, marginTop: 6 }]}>JUGADOR</Text>
        {subiendo && <ActivityIndicator color={lp.green} style={{ marginTop: 10 }} />}
        <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
          <TouchableOpacity style={fotoBtn} onPress={cambiarFoto} disabled={subiendo}>
            <Text style={fotoBtnTxt}>Cambiar foto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[fotoBtn, { borderColor: lp.danger }]} onPress={quitarFoto} disabled={subiendo}>
            <Text style={[fotoBtnTxt, { color: lp.danger }]}>Quitar foto</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Stats */}
      <View style={{ flexDirection: "row", gap: 10, marginBottom: 18 }}>
        <View style={[box, { backgroundColor: lp.green }]}>
          <Text style={boxNum}>{stats.goles}</Text><Text style={boxLbl}>GOLES</Text>
        </View>
        <View style={[box, { backgroundColor: lp.accent }]}>
          <Text style={boxNum}>{stats.partidos}</Text><Text style={boxLbl}>PARTIDOS</Text>
        </View>
      </View>

      {/* Accesos */}
      <OpcionMenu icono="edit" texto="Editar datos personales" onPress={() => setEditar(true)} />
      <OpcionMenu icono="creditcard" texto="Métodos de pago" onPress={() => Alert.alert("Métodos de pago", "Disponible próximamente.")} />
      <OpcionMenu icono="lock" texto="Cambiar contraseña" onPress={() => navigation.navigate("ChangePassword")} />
      <OpcionMenu icono="logout" texto="Cerrar sesión" color={lp.danger} onPress={cerrarSesion} />

      <EditarPerfilModal
        visible={editar}
        nombreInicial={me?.nombre || ""}
        telefonoInicial={me?.telefono || ""}
        acento={lp.accent}
        onCerrar={() => setEditar(false)}
        onGuardado={(actualizado) => setMe(actualizado)}
      />
    </ScrollView>
  );
}

const fotoBtn = { borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 14 };
const fotoBtnTxt = { color: lp.green, fontWeight: "700", fontSize: 13 };
const box = { flex: 1, borderRadius: 14, paddingVertical: 18, alignItems: "center" };
const boxNum = { color: lp.white, fontSize: 26, fontWeight: "800" };
const boxLbl = { color: "rgba(255,255,255,0.9)", fontSize: 11, fontWeight: "700", letterSpacing: 1, marginTop: 2 };
```

- [ ] **Step 2: Comprobar que no quedan emojis ni código muerto**

```bash
cd mobile && grep -nP "[\x{1F300}-\x{1FAFF}\x{2716}\x{270E}\x{2297}]" src/screens/player/PlayerProfileScreen.js; echo "coincidencias: $?"
grep -c "ImagePicker\|Modal\|TextInput\|function Opcion" src/screens/player/PlayerProfileScreen.js
```

Esperado: el `grep` de emojis no encuentra nada (`$?` = 1), y el segundo cuenta `0` — esa lógica se fue a las piezas compartidas.

- [ ] **Step 3: Verificar la sintaxis**

```bash
cd mobile && node scripts/verificar-sintaxis.cjs src/screens/player/PlayerProfileScreen.js
```

Esperado: `OK    src/screens/player/PlayerProfileScreen.js`

- [ ] **Step 4: Commit**

```bash
git add mobile/src/screens/player/PlayerProfileScreen.js
git commit -m "feat(movil): iconos en el menu de perfil del jugador"
```

---

## Task 4: Perfil de entrenador y árbitro

**Files:**
- Create: `mobile/src/screens/PerfilScreen.js`
- Delete: `mobile/src/screens/coach/PerfilScreen.js`
- Modify: `mobile/App.js` (línea 25, el import)

**Interfaces:**
- Consumes: `Icono`, `OpcionMenu`, `useFotoPerfil`, `EditarPerfilModal` de Tasks 1-2.

Se mueve fuera de `screens/coach/` porque `RefereeTabs` también la monta (`App.js`, `CoachTabs` y `RefereeTabs`).

- [ ] **Step 1: Mover el archivo con git**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol
git mv mobile/src/screens/coach/PerfilScreen.js mobile/src/screens/PerfilScreen.js
```

Usa `git mv`, no `cp` + `rm`: conserva el historial del archivo.

- [ ] **Step 2: Reescribir el archivo movido**

Sustituye el contenido completo de `mobile/src/screens/PerfilScreen.js` por:

```js
// PERFIL de entrenador y árbitro (ambos paneles montan esta pantalla).
// Misma estructura que la del jugador, sin cajas de estadísticas: no existe
// endpoint de stats agregadas para estos roles.
import React, { useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import Avatar from "../components/Avatar";
import EditarPerfilModal from "../components/EditarPerfilModal";
import OpcionMenu from "../components/OpcionMenu";
import useFotoPerfil from "../hooks/useFotoPerfil";
import { useAuth } from "../auth";
import { lp, ls } from "../publicTheme";

// El acento sigue a la cabecera de cada panel: dorada la del entrenador,
// guinda la del árbitro (ver goldHeader/maroonHeader en App.js).
const ACENTO = { entrenador: lp.gold, arbitro: lp.maroon };

export default function PerfilScreen({ navigation }) {
  const { usuario, logout } = useAuth();
  const [editar, setEditar] = useState(false);
  const { subiendo, fotoV, cambiarFoto, quitarFoto } = useFotoPerfil();

  const acento = ACENTO[usuario?.rol] || lp.accent;
  const nombreMostrar = usuario?.nombre || "Usuario";

  async function cerrarSesion() {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: "Public" }] });
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Encabezado */}
      <View style={{ alignItems: "center", marginVertical: 12 }}>
        <Avatar usuarioId={usuario?.id} nombre={nombreMostrar} size={72} version={fotoV} />
        <Text style={{ color: lp.textDark, fontSize: 20, fontWeight: "800", marginTop: 12 }}>{nombreMostrar}</Text>
        <Text style={[ls.badge, { backgroundColor: lp.surface, color: acento, borderWidth: 1, borderColor: lp.surfaceBorder, marginTop: 6 }]}>
          {(usuario?.rol || "").toUpperCase()}
        </Text>
        {/* El jugador no muestra el correo; aquí sí estaba antes y no se le quita. */}
        <Text style={{ color: lp.textMuted, fontSize: 13, marginTop: 6 }}>{usuario?.correo}</Text>
        {subiendo && <ActivityIndicator color={acento} style={{ marginTop: 10 }} />}
        <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
          <TouchableOpacity style={fotoBtn} onPress={cambiarFoto} disabled={subiendo}>
            <Text style={[fotoBtnTxt, { color: acento }]}>Cambiar foto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[fotoBtn, { borderColor: lp.danger }]} onPress={quitarFoto} disabled={subiendo}>
            <Text style={[fotoBtnTxt, { color: lp.danger }]}>Quitar foto</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Accesos */}
      <OpcionMenu icono="edit" texto="Editar datos personales" onPress={() => setEditar(true)} />
      <OpcionMenu icono="creditcard" texto="Métodos de pago" onPress={() => Alert.alert("Métodos de pago", "Disponible próximamente.")} />
      <OpcionMenu icono="lock" texto="Cambiar contraseña" onPress={() => navigation.navigate("ChangePassword")} />
      <OpcionMenu icono="logout" texto="Cerrar sesión" color={lp.danger} onPress={cerrarSesion} />

      <EditarPerfilModal
        visible={editar}
        nombreInicial={usuario?.nombre || ""}
        telefonoInicial={usuario?.telefono || ""}
        acento={acento}
        onCerrar={() => setEditar(false)}
        onGuardado={() => {}}
      />
    </ScrollView>
  );
}

const fotoBtn = { borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 14 };
const fotoBtnTxt = { fontWeight: "700", fontSize: 13 };
```

Nota sobre `onGuardado`: aquí no hace falta refrescar estado local porque la pantalla lee de `usuario`, y `EditarPerfilModal` ya llama a `refrescar()` de `useAuth` antes de invocar el callback.

- [ ] **Step 3: Actualizar el import en App.js**

En `mobile/App.js`, línea 25, cambia:

```js
import PerfilScreen from "./src/screens/coach/PerfilScreen";
```

por:

```js
import PerfilScreen from "./src/screens/PerfilScreen";
```

- [ ] **Step 4: Comprobar que no queda ninguna referencia a la ruta vieja**

```bash
cd mobile && grep -rn "coach/PerfilScreen" . --exclude-dir=node_modules; echo "coincidencias: $?"
```

Esperado: sin salida y `$?` = 1.

- [ ] **Step 5: Verificar la sintaxis**

```bash
cd mobile && node scripts/verificar-sintaxis.cjs src/screens/PerfilScreen.js App.js
```

Esperado: dos líneas `OK` y exit 0.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/screens/PerfilScreen.js mobile/App.js
git commit -m "feat(movil): menu de perfil para entrenador y arbitro"
```

---

## Task 5: Campanita de notificaciones

**Files:**
- Modify: `mobile/src/screens/player/PlayerHomeScreen.js:11-19`

**Interfaces:**
- Consumes: `Icono` de Task 1.

- [ ] **Step 1: Añadir el import**

En `mobile/src/screens/player/PlayerHomeScreen.js`, tras la línea que importa `apiGet`, añade:

```js
import Icono from "../../components/Icono";
```

- [ ] **Step 2: Sustituir el emoji**

Cambia la función `Campanita` (líneas 11-19). De:

```js
function Campanita({ onPress, hayNuevas }) {
  return (
    <TouchableOpacity onPress={onPress} style={{ paddingHorizontal: 14 }}>
      <Text style={{ fontSize: 20 }}>🔔</Text>
      {hayNuevas && <View style={{ position: "absolute", right: 10, top: 0, width: 10, height: 10, borderRadius: 5, backgroundColor: lp.red }} />}
    </TouchableOpacity>
  );
}
```

a:

```js
function Campanita({ onPress, hayNuevas }) {
  return (
    <TouchableOpacity onPress={onPress} style={{ paddingHorizontal: 14 }}>
      {/* La cabecera del panel del jugador es verde, así que la campana va en blanco. */}
      <Icono nombre="bell" size={20} color={lp.white} />
      {hayNuevas && <View style={{ position: "absolute", right: 10, top: 0, width: 10, height: 10, borderRadius: 5, backgroundColor: lp.red }} />}
    </TouchableOpacity>
  );
}
```

El punto rojo de "hay nuevas" no se toca.

- [ ] **Step 3: Comprobar que el emoji se fue y que `Text` sigue usándose**

```bash
cd mobile && grep -n "🔔" src/screens/player/PlayerHomeScreen.js; echo "campana: $?"
grep -c "<Text" src/screens/player/PlayerHomeScreen.js
```

Esperado: sin coincidencias de 🔔 (`$?` = 1) y el conteo de `<Text` mayor que 0 — el import de `Text` sigue haciendo falta en el resto de la pantalla, no lo quites.

- [ ] **Step 4: Verificar la sintaxis**

```bash
cd mobile && node scripts/verificar-sintaxis.cjs src/screens/player/PlayerHomeScreen.js
```

Esperado: `OK    src/screens/player/PlayerHomeScreen.js`

- [ ] **Step 5: Commit**

```bash
git add mobile/src/screens/player/PlayerHomeScreen.js
git commit -m "feat(movil): icono en la campanita de notificaciones"
```

---

## Task 6: Verificación de rama y checklist de dispositivo

**Files:**
- Create: `docs/superpowers/checklist-iconos-perfil-movil.md`

- [ ] **Step 1: Verificar la sintaxis de todo lo tocado**

```bash
cd mobile && node scripts/verificar-sintaxis.cjs \
  App.js \
  src/components/Icono.js \
  src/components/OpcionMenu.js \
  src/components/EditarPerfilModal.js \
  src/hooks/useFotoPerfil.js \
  src/screens/PerfilScreen.js \
  src/screens/player/PlayerProfileScreen.js \
  src/screens/player/PlayerHomeScreen.js
echo "sintaxis exit=$?"
node scripts/verificar-iconos.cjs
```

Esperado: ocho líneas `OK`, `sintaxis exit=0` y `OK: 5 iconos válidos`.

- [ ] **Step 2: Confirmar que no se tocó el backend**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol
git diff --stat main...HEAD -- api/ web/; echo "cambios en api/web: $?"
```

Esperado: sin salida. Si aparece algo, **para** — el spec prohíbe tocar `api/` y `web/`.

- [ ] **Step 3: Correr la suite de Python**

```bash
cd /home/vikca/sistema-torneos/sistema-futbol/api && .venv/bin/python -m pytest -q
```

Esperado: `233 passed`. Tarda unos 4 minutos. No cubre `mobile/`; se corre para confirmar que no hay daño colateral.

- [ ] **Step 4: Escribir el checklist de dispositivo**

Crea `docs/superpowers/checklist-iconos-perfil-movil.md`:

```markdown
# Checklist de validación en dispositivo — iconos y menú de perfil

Lo estático ya está verificado (babel en los 8 archivos, 5 iconos válidos, 233
tests de Python en verde). Esto cubre lo único que no se puede probar sin un
teléfono: que los SVG rendericen y que los tres roles vean su menú.

## Preparación
1. Backend arriba: `docker compose up -d`.
2. `mobile/app.json` → `extra.apiUrl` apuntando a la IP LAN de tu PC.
3. `cd mobile && npx expo start --tunnel` y escanea el QR con Expo Go.

> `react-native-svg` viene incluido en Expo Go: no hace falta build personalizado.

## 1. Jugador — jugador@demo.com / demo1234
- [ ] **INICIO**: la campana de la cabecera es un icono de línea blanco, no un emoji.
- [ ] Con notificaciones sin leer, el punto rojo sigue apareciendo sobre la campana.
- [ ] Pulsar la campana sigue abriendo NOTIFICACIONES.
- [ ] **MI PERFIL**: las 4 filas muestran iconos (lápiz, tarjeta, candado, salida),
      no emojis. El de "Cerrar sesión" es rojo, como su texto.
- [ ] "Editar datos personales" abre el modal con tu nombre y teléfono ya puestos;
      guardar actualiza el nombre de la cabecera.
- [ ] "Cambiar contraseña" navega. "Métodos de pago" avisa "Disponible próximamente".
- [ ] Cambiar y quitar foto siguen funcionando (no debe haber regresión del PR #20).

## 2. Entrenador — entrenador@demo.com / demo1234
- [ ] **PERFIL** ya no es la lista de botones vieja: avatar, nombre, insignia
      **ENTRENADOR** en dorado, correo debajo, y las 4 filas con iconos.
- [ ] "Editar datos personales" (nuevo para este rol) abre el modal, guarda y el
      nombre cambia. El botón "Guardar" es dorado.
- [ ] Cambiar y quitar foto funcionan; el avatar se actualiza sin reiniciar.
- [ ] "Cerrar sesión" vuelve al área pública.

## 3. Árbitro — arbitro@demo.com / demo1234
- [ ] **PERFIL** idéntico al del entrenador pero con la insignia **ARBITRO** en
      guinda y el botón "Guardar" guinda.
- [ ] "Editar datos personales" guarda correctamente.
- [ ] Cambiar y quitar foto funcionan.

## Si algo falla
Anota **rol, pantalla y qué viste** (o captura). Lo más probable:
1. Icono en blanco → nombre mal escrito en `OpcionMenu` (`edit`, `creditcard`,
   `lock`, `logout`, `bell`).
2. Icono negro sólido donde debería ser de línea → falta `trazo: true` en
   `iconos-datos.json`.
3. Pantalla en blanco al abrir Perfil → import roto tras mover `PerfilScreen`.
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/checklist-iconos-perfil-movil.md
git commit -m "docs(movil): checklist de validacion en dispositivo"
```

- [ ] **Step 6: Entregar al usuario para validación**

Pásale el checklist. **No abras el PR hasta que confirme en dispositivo.** Los dos bugs del PR #20 (`Authorization` en `<Image>`, z-index en la web) se escaparon a la verificación estática; el trabajo no se declara probado hasta que lo vea en el teléfono.

---

## Auto-revisión del plan

**Cobertura del spec:**

| Requisito del spec | Tarea |
|---|---|
| `Icono.js` espejo del macro web, 5 iconos, viewBox 24 | Task 1 |
| `react-native-svg` 15.2.0 vía `npx expo install` | Task 1, Step 1 |
| Extraer del paquete `reicon` solo a scratchpad | Global Constraints (paths ya extraídos e incrustados en Task 1) |
| `OpcionMenu`, `EditarPerfilModal`, `useFotoPerfil` | Task 2 |
| 4 emojis del perfil del jugador → iconos | Task 3 |
| `PerfilScreen` movida y reescrita, acento por rol, correo conservado | Task 4 |
| `App.js` import actualizado | Task 4, Step 3 |
| Campanita `🔔` → icono, punto rojo intacto | Task 5 |
| Sin cambios en `api/` ni `web/` | Task 6, Step 2 (comprobación activa) |
| Suite Python en 233 | Task 6, Step 3 |
| Validación en dispositivo con checklist | Task 6, Steps 4-6 |
| Fuera de alcance: NotificationsScreen, HomeScreen, CoachHomeScreen, eventos | Ninguna tarea los toca |

Sin huecos.

**Consistencia de nombres** (verificada entre tareas): `ICONOS` con claves `edit`/`creditcard`/`lock`/`logout`/`bell`; campos `d`/`trazo`/`parImpar`; props de `Icono` `nombre`/`size`/`color`; props de `OpcionMenu` `icono`/`texto`/`onPress`/`color`; retorno de `useFotoPerfil` `subiendo`/`fotoV`/`cambiarFoto`/`quitarFoto`; props de `EditarPerfilModal` `visible`/`nombreInicial`/`telefonoInicial`/`acento`/`onCerrar`/`onGuardado`. Todas coinciden en las Tasks 1-5.

**Riesgo conocido, sin mitigar en el plan:** si `react-native-svg` fallara en Expo Go, el plan B (documentado en el spec) es `@expo/vector-icons`, que ya está instalado. Se detectaría en Task 6, Step 6.

**Dos correcciones aplicadas al escribir el plan**, ambas descubiertas al probar los comandos en vez de darlos por buenos:

1. **`npx babel` no sirve como verificador.** Resuelve al paquete `babel` v6 deprecado del caché de npx, no a `@babel/cli`. Se comprobó que hace fallar un archivo válido (`_probe-uso.js`, un import de JSON perfectamente legal). El plan usa ahora `@babel/core` directamente, y la Task 1 Step 3 **exige comprobar que el verificador detecta un archivo roto** antes de fiarse de él. Consecuencia colateral: la nota "3/3 babel OK" del ledger del PR #20 se apoyaba en ese comando, así que su valor probatorio era dudoso.

2. **Los datos de iconos van en JSON, no en un `.js` con `export default`.** `mobile/package.json` no declara `"type": "module"`; el `import` desde el verificador solo funcionaba por la autodetección de sintaxis de Node ≥ 22.7 (con warning `MODULE_TYPELESS_PACKAGE_JSON`), y habría reventado en cualquier Node anterior. Verificado en este repo que JSON lo lee `require()` sin transpilar y que el bundler acepta el `import` del `.json`.
