# Iconos en eventos de partido y emojis restantes (móvil)

Fecha: 2026-07-28
Estado: aprobado por el usuario, pendiente de plan de implementación

## Problema

Tercera y última tanda de iconos de la app móvil. Los PRs #21 y #22 cubrieron el
menú de perfil, la campanita, la barra de navegación y cuatro pantallas. Quedan
**22 líneas** con caracteres usados como iconos, y se parten en dos naturalezas:

- **14 de color** (`⚽ 🅰 🟨 🟥 📨 📎 🏆 🔔 🔁`): emoji multicolor, dependen de la
  fuente del sistema, cambian de forma entre Android e iOS y no heredan el color
  del tema.
- **8 tipográficos** (`✓ ✕ ↑ ↓ →`): glifos monocromos que ya heredan color y
  tamaño de su estilo, y se comportan igual en ambas plataformas.

Esta tanda ataca los 14 de color.

## Alcance

**Dentro** — las 14 líneas de emoji de color:

| Archivo | Línea(s) | Emoji |
|---|---|---|
| `src/components/LineupPitch.js` | 18-21 | `⚽ 🅰 🟨 🟥` |
| `src/screens/referee/RefLiveScreen.js` | 9, 15, 17 | `⚽ 🟨 🟥 🔁` |
| `src/screens/referee/RefSummaryScreen.js` | 73, 86 | `⚽ 🟨 🟥` |
| `src/screens/player/NotificationsScreen.js` | 11, 13, 15 | `⚽ 🏆 🔔` (de sus 5 ramas; `$` y `!` quedan) |
| `src/screens/HomeScreen.js` | 55 | `📨` |
| `src/screens/RegisterStaffScreen.js` | 114 | `📎` |

**Dentro también:** ampliar `mobile/scripts/verificar-nombres-iconos.cjs` (ver §5).

**Fuera** — los 8 tipográficos, decisión explícita del usuario:
`✓` en `RefEventScreen:34`, `RefSummaryScreen:98` y `RefHistoryScreen:41`;
`✕` en `NotificationsScreen:90` y `TeamEditScreen:117`;
`↑ ↓` en `LineupPitch:22-23`; `→` en `LoginScreen:68`.

**Fuera también:** ningún cambio en `api/` ni en `web/`. No se añaden endpoints.

## Decisiones tomadas

| Decisión | Elegido | Por qué |
|---|---|---|
| Alcance | Solo los 14 de color | Los tipográficos no tienen el problema que motiva el trabajo: ya heredan color y se ven igual en ambas plataformas. Convertir un `✓` embebido en la frase "acta enviada ✓" obligaría a partir el texto sin ganar nada. |
| Distintivo de asistencia | Una **"A" de texto con estilo**, no un icono | La web no iconizó asistencias: no hay precedente ni metáfora establecida. `Share` se lee universalmente como "compartir" y `Handshake` es ilegible a 14 px, que es el tamaño de un distintivo. La letra comunica lo mismo que `🅰️` sin sus defectos. |
| Iconos de evento | Los mismos que la web (`football`, `tarjeta`, `transfer`) | El panel ya los resolvió en el PR #20. Reutilizarlos evita que el mismo evento tenga dos formas entre plataformas. |
| Color de la tarjeta roja | `lp.danger` (`#c0392b`), **sin** paridad con la web | El panel es oscuro y usa `#ff5a5a`; la app es clara. El mismo rojo en ambos fondos se vería mal en uno de los dos. El amarillo sí se copia: `#f2b53c`. |
| Verificador de nombres | Se **amplía en esta tanda**, no se deja anotado | Ver §5. |

## Catálogo: 16 → 20 iconos

| Clave | Origen | Tipo |
|---|---|---|
| `transfer` | macro `web/app/templates/_iconos.html` | relleno, 2 paths |
| `tarjeta` | macro web, **convertido de `<rect>` a path** | relleno, 1 path |
| `envelope` | Reicon `Envelope` | relleno, 1 path |
| `paperclip` | Reicon `Paperclip` | relleno, 1 path |

`⚽`, `🏆` y `🔔` ya están cubiertos por `football`, `cuptrophy` y `bell`, en el
catálogo desde los PRs #21 y #22.

Los datos se producen con `mobile/scripts/generar-iconos.cjs`, ampliando sus
mapas `DESDE_WEB` y `DESDE_REICON`. El paquete `reicon@1.1.103` se descarga a
scratchpad y **nunca** entra en `node_modules` ni en `package.json`.

### La tarjeta es un `<rect>`, y esta vez la conversión no pierde nada

El `tarjeta` del macro web es el segundo icono del panel que no está hecho de
paths: `<rect x="6" y="2.5" width="12" height="19" rx="2.2"/>`. Con `location`
(PR #22) el problema fue irresoluble sin extender `Icono.js`, porque mezclaba
`circle`, `line` y un `g transform`. Un rectángulo redondeado, en cambio, se
expresa **exactamente** como path:

```
M8.2 2.5 H15.8 A2.2 2.2 0 0 1 18 4.7 V19.3 A2.2 2.2 0 0 1 15.8 21.5
H8.2 A2.2 2.2 0 0 1 6 19.3 V4.7 A2.2 2.2 0 0 1 8.2 2.5 Z
```

Móvil y web pintan la misma forma, y `Icono.js` **no se modifica**. La conversión
la hace el generador, no una transcripción a mano.

### Paleta

Se añade `amarilla: "#f2b53c"` a `lp` en `mobile/src/publicTheme.js`, copiado de
`.ic-amarilla` del panel. La roja **no** siempre reutiliza `lp.danger`
(`#c0392b`): sobre el verde de la cancha (`#1C6B3A`) ese rojo da **1.20:1** de
contraste, inservible. Se añade un segundo tono, `rojaClara: "#ff5a5a"`, para ese
caso. Hay entonces dos rojos con usos distintos:

- `lp.danger` (`#c0392b`) — listas de eventos sobre fondo claro (`RefLiveScreen`,
  `RefSummaryScreen`), donde da 5.21:1.
- `lp.rojaClara` (`#ff5a5a`) — distintivos de `LineupPitch`, calibrado para el
  verde de la cancha. Se reutiliza tal cual en la banca.

**Contraste medido, sin adornos.** Ratios WCAG de cada tono contra los dos fondos
donde aparece (cancha `#1C6B3A`, banca `#FBFAF6`):

| Tono | Cancha | Banca |
|---|---|---|
| `amarilla` `#f2b53c` | 3.56:1 | **1.76:1** |
| `rojaClara` `#ff5a5a` | **2.14:1** | 2.93:1 |
| `danger` `#c0392b` | 1.20:1 | 5.21:1 |
| tinte blanco | 6.53:1 | — |
| tinte `textDark` | — | 14.40:1 |

Los dos valores en negrita quedan por debajo del 3:1 que se pide a un objeto
gráfico. **Se acepta a sabiendas**, por tres razones: el color de la tarjeta
identifica su tipo y atarlo al fondo lo volvería ambiguo; son rectángulos
rellenos de 11 px, cuya forma se lee por el borde y no por la luminancia; y el
emoji anterior (`🟨`, `🟥`) tenía el mismo tono sobre el mismo fondo, así que no
hay regresión respecto a lo que ya había.

Lo que **sí** era una regresión, y está corregido, es el **tinte base** de los
distintivos sin color propio (balón, `A`, `×N`, flechas): un blanco fijo dejaba
1.04:1 sobre la banca. Ahora el tinte lo decide el contenedor: blanco en la
cancha, `lp.textDark` en la banca.

Si en la validación en dispositivo alguno de los dos tonos flojos estorba, la
corrección es recalibrar ese tono en `publicTheme.js`, no hacerlo depender del
fondo.

## Cambios por pantalla

### Directos

- **`HomeScreen:55`** — `📨 Mis invitaciones a equipos` pasa a fila: icono
  `envelope` como hermano del texto.
- **`RegisterStaffScreen:114`** — igual con `paperclip`. Ojo: el texto es
  condicional (`archivo ? \`📎 ${archivo.name}\` : "Adjuntar documento"`), así que
  el icono solo se pinta cuando hay archivo.
- **`NotificationsScreen:9-16`** — la función `ICONO(titulo)` tiene **cinco** ramas,
  y solo tres llevan emoji. Las otras dos ya son caracteres de texto y **quedan como
  están**, por la misma razón que los tipográficos están fuera de alcance:

  | Rama | Hoy | Después |
  |---|---|---|
  | `gol` | `⚽` | `icono: "football"` |
  | `pago` | `"$"` | **sin cambio** |
  | `torneo` | `🏆` | `icono: "cuptrophy"` |
  | `convocatoria` | `"!"` | **sin cambio** |
  | resto | `🔔` | `icono: "bell"` |

  Eso obliga a que el objeto devuelto admita las dos formas: `{ icono, bg }` para
  las tres convertidas y `{ texto, bg }` para `$` y `!`. El render pinta `<Icono>`
  si viene `icono`, y `<Text>` si viene `texto`. **No unifiques las cinco ramas a
  icono**: `$` y `!` no tienen equivalente sensato en el catálogo y no son el
  problema que esta tanda resuelve.

### Medio

- **`RefSummaryScreen:73,86`** — el emoji va interpolado dentro del `<Text>` junto
  al minuto y el nombre del jugador. El texto se conserva; el icono pasa a hermano
  en una fila. La línea 86 elige entre roja y amarilla por `t.tipo`, y esa decisión
  pasa de elegir emoji a elegir **color** sobre el mismo icono `tarjeta`.

### Estructurales

- **`RefLiveScreen`** — `resumenEvento(e)` devuelve hoy **una cadena** que la línea
  117 pinta como `<Text>`. Pasa a devolver `{ icono, color, texto }`, y la línea
  117 se convierte en una fila con icono y texto. Es el cambio de mayor alcance del
  lote. El objeto `ICONO` de la línea 9 pasa de emoji a nombres de icono.

- **`LineupPitch`** — `badgesDe()` devuelve hoy `{ key, texto }` con valores como
  `"⚽×3"`. Pasa a `{ key, icono, color, veces }`, y `Distintivos` pinta el icono
  más un `×N` al lado cuando `veces > 1`. La asistencia es el caso aparte:
  `{ key: "asist", letra: "A", veces }`, renderizada como texto con estilo en vez
  de icono. `↑` y `↓` (entra/sale) **no se tocan**: son tipográficos.

## §5. Ampliación del verificador de nombres

`mobile/scripts/verificar-nombres-iconos.cjs` solo detecta literales
`nombre="…"`. Hoy tiene **2 puntos ciegos** (`nombre={a.icono}` en
`CoachHomeScreen`, `nombre={icono}` en `OpcionMenu`). Esta tanda añadiría **2 más**
—los distintivos de `LineupPitch` y la lista de eventos de `RefLiveScreen`— y los
nuevos están en la pantalla del árbitro en vivo, la más visible de la app.

Por eso se amplía ahora en vez de dejarlo anotado. Dos cambios:

1. **Reconocer también la prop `icono`** en sus dos formas: `icono="…"` (JSX, como
   en `<OpcionMenu icono="edit">`) e `icono: "…"` (objeto, como en el array
   `ACCIONES` y en los nuevos de esta tanda). Todos los valores que hoy son
   invisibles **son literales en el fuente**, solo que bajo otra prop, así que esto
   cierra el hueco entero.
2. **Acotar la búsqueda de `nombre=` al componente `<Icono>`.** Hoy la regex acepta
   cualquier `nombre="…"`, y `<Avatar>` tiene la misma prop. No hay conflicto
   todavía porque los cinco usos de `Avatar` son dinámicos, pero un
   `<Avatar nombre="juan">` daría un falso positivo.

Límite que **permanece** y debe quedar documentado en la cabecera: un valor
calculado en tiempo de ejecución sigue siendo invisible. La ampliación cubre lo
que hoy existe y lo previsible, no la cobertura teórica completa.

## Flujo de datos

Ninguno nuevo. `Icono` es presentacional puro y ninguna pantalla cambia qué pide
al API. Lo que cambia es la **forma de los datos internos** en tres sitios:
`NotificationsScreen` (`e` → `icono`), `RefLiveScreen` (string → objeto) y
`LineupPitch` (`texto` → `icono`/`letra` + `veces`). Los tres son estructuras
locales, no contratos con el backend.

## Manejo de errores

Sin cambios. Un `nombre` desconocido en `Icono` degrada a hueco vacío en vez de
lanzar. En `LineupPitch` y `RefLiveScreen`, un tipo de evento no contemplado debe
seguir renderizando el texto sin icono, como hace hoy con `ICONO[e.tipo] || ""`.

## Verificación

1. `npm run verificar` sobre cada archivo tocado (usa el `@babel/core` del
   proyecto; **nunca `npx babel`**, que resuelve a un paquete v6 deprecado del
   caché de npx y da falsos negativos).
2. `npm run verificar-iconos` con la lista ampliada a **20** claves.
3. `npm run verificar-nombres` **ampliado**, incluida una prueba de que detecta una
   errata en las formas nuevas (`icono="…"` e `icono: "…"`), no solo en `nombre=`.
4. Suite de Python completa — debe seguir en **233**. No se toca `api/` ni `web/`.
   Tarda **~12,5 minutos**.
5. **Validación en dispositivo con Expo Go.** Requiere un partido con goles,
   tarjetas y cambios registrados: es la única forma de ver los distintivos de la
   cancha y la lista de eventos en vivo con datos reales.

No hay runner de tests JS: nada cubre `mobile/`. Un defecto que solo se manifieste
en ejecución no lo detecta ninguna de las cuatro primeras.

## Riesgos

- **Los dos cambios estructurales tocan lógica, no solo presentación.**
  `resumenEvento()` y `badgesDe()` cambian su tipo de retorno, y sus consumidores
  con ellos. Es el primer trabajo de estas tres tandas que puede romper
  comportamiento, no solo aspecto.
- **Los distintivos con multiplicador.** `"⚽×3"` era una sola cadena; ahora son dos
  elementos. Un jugador con dos goles, una amarilla y una asistencia apila cuatro
  distintivos sobre su foto, en un espacio de unos 14 px de alto.
- **Validar los eventos exige datos.** Sin un partido con goles y tarjetas no se
  puede comprobar nada de lo estructural; el checklist debe decir cómo prepararlo.
