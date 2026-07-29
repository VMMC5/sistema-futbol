# Iconos en la barra de navegación y en las pantallas restantes (móvil)

Fecha: 2026-07-28
Estado: aprobado por el usuario, pendiente de plan de implementación

## Problema

El PR #21 sustituyó los emojis del menú de perfil y la campanita por SVG de Reicon,
pero dejó fuera el resto de la app (decisión explícita de alcance en aquel momento).
Quedan emojis como iconos en cuatro pantallas, y la barra de navegación inferior
nunca ha tenido iconos: hoy cada pestaña muestra un punto de 6 px.

## Alcance

**Dentro:**

- **Barra de navegación inferior** de los cuatro `Tab.Navigator` (pública,
  entrenador, árbitro, jugador). Es lo único genuinamente nuevo.
- `TorneosScreen` — `🏆` del círculo de cada torneo.
- `PlayerHomeScreen` — `📊` "Ver mis estadísticas" y `📅` "Próximos partidos".
- `ReservarScreen` — `📍` del buscador de sede.
- `CoachHomeScreen` — `👥 📝 📋 📅` de la rejilla de acciones.

**Fuera** (sin cambios respecto a la decisión del PR #21):

- `NotificationsScreen` — `⚽ 🏆 🔔` por tipo de aviso y la `✕` de descartar.
- `HomeScreen` — `📨`.
- `RefLiveScreen`, `RefSummaryScreen`, `LineupPitch` — `⚽ 🟨 🟥 🔁 ↑ ↓` de
  eventos de partido.
- `RegisterStaffScreen` — `📎`.
- Los `✓` de `RefEventScreen`, `RefHistoryScreen` y `RefSummaryScreen`, y las `✕`
  de `TeamEditScreen`.

**Fuera también:** ningún cambio en `api/` ni en `web/`. No se añaden endpoints.

## Decisiones tomadas

| Decisión | Elegido | Por qué |
|---|---|---|
| Indicador de pestaña | El icono **sustituye** al punto de 6 px | Patrón estándar de iOS y Android. React Navigation ya inyecta el color correcto (`lp.accent` activa, `lp.textMuted` inactiva), que es justo lo que `<Icono>` acepta. |
| Etiquetas de texto de las pestañas | Se conservan | "Reservar" e "Historial" no tienen un icono universalmente reconocible. |
| Mapeo concepto→icono | Copiado del menú del panel web | El web ya lo resolvió en el PR #18. Reutilizarlo evita que el mismo concepto tenga dos formas distintas entre plataformas. |
| Icono de Inicio | `home` (Reicon `Home`) | Elección del usuario. La propuesta inicial era `category`, que es lo que la web usa para Dashboard. |
| Icono de Alineación | `clipboardlist` (Reicon `ClipboardList`) | Elección del usuario. La propuesta inicial era `checklist`. |
| Icono de Inscribir | `docadd` (Reicon `DocAdd`) | Elección del usuario. La propuesta inicial era reutilizar `edit`. |
| `📍` de buscar sede | Sale del `placeholder` y pasa a ser un hermano del `TextInput` | Un `placeholder` es un **string**, no admite un componente. Es el único cambio estructural de la tanda. |

## Catálogo de iconos: de 5 a 16

Cinco iconos se copian del macro `web/app/templates/_iconos.html` (paths ya en el
repo y verificados); seis se extraen del paquete npm `reicon@1.1.103`, que se
descarga **solo a scratchpad**, nunca a `node_modules` ni a `package.json` —
igual que en los PRs #18 y #21.

| Clave | Origen | Tipo |
|---|---|---|
| `cuptrophy` | macro web (Torneos) | relleno, 2 paths |
| `chart` | macro web (Estadísticas) | relleno, 1 path |
| `calendar` | macro web (Reservas) | relleno, 7 paths |
| `people` | macro web (Usuarios) | trazo, 6 paths |
| `football` | macro web (Partidos) | relleno, 1 path |
| `home` | Reicon `Home` | relleno, 2 paths |
| `user` | Reicon `User` | relleno, 2 paths |
| `history` | Reicon `History` | relleno, 1 path |
| `clipboardlist` | Reicon `ClipboardList` | relleno, 1 path |
| `docadd` | Reicon `DocAdd` | relleno, 1 path |
| `location` | Reicon `Pin` | relleno, 1 path |

Las claves siguen la convención ya establecida: minúsculas, sin separadores
(`creditcard`, `clipboardlist`, `docadd`).

**`location` NO se copia del macro web, y el motivo importa.** El `location` de la
web es el único icono del macro que no está hecho solo de `<path>`: usa `<circle>`,
`<line>` y un `<g transform="scale(1.33333)">`. El modelo de datos de
`iconos-datos.json` es un array de paths, así que copiarlo obligaría a extender
`Icono.js` para soportar tres elementos SVG más y transformaciones de grupo —
mucha complejidad por un icono. Se usa `Pin` de Reicon, que es un marcador de mapa
de un solo path. **Consecuencia asumida:** el icono de sede será visualmente
distinto entre web y móvil, la única excepción a la paridad. Se descartó `Gps`
(también de un path) porque es una diana, no un marcador.

**Nota de coherencia visual:** `people` es de trazo, y `edit` ya lo era. Los otros
catorce son de relleno. En la rejilla del entrenador conviven `people` (trazo) con
`docadd`, `clipboardlist` y `calendar` (relleno), así que "Mis equipos" se verá más
ligero que sus tres vecinos. Es fiel a Reicon y a lo que ya hace la web; se acepta
a sabiendas. Si al verlo en el dispositivo desentona, la corrección es cambiar
`people` por una variante de relleno, no alterar `Icono.js`.

## Arquitectura

### `mobile/src/components/iconos-datos.json` — se amplía

Once entradas nuevas, mismo formato que las cinco existentes:
`{ d: string[], trazo?: boolean, parImpar?: boolean }`. `Icono.js` **no cambia**:
su contrato (`{ nombre, size = 18, color }`) ya cubre todos los casos, y un nombre
desconocido sigue degradando a hueco vacío.

### `mobile/scripts/verificar-iconos.cjs` — se amplía

Su lista `ESPERADOS` está fijada a los cinco iconos actuales y **fallaría** al ver
dieciséis: valida tanto que no falte ninguno como que no sobre ninguno. Pasa a las
dieciséis claves. Sin este cambio, la verificación de la tanda no arranca.

### `mobile/App.js` — barra de navegación

Se elimina la función `Punto`. Cada `Tab.Screen` declara su icono:

```js
<Tab.Screen
  name="Inicio"
  component={PlayerHomeScreen}
  options={{ title: "INICIO", tabBarIcon: ({ color }) => <Icono nombre="home" size={22} color={color} /> }}
/>
```

Se retira `tabBarIcon` del bloque `screenOptions` compartido de los cuatro
navegadores, donde hoy pinta el `Punto`.

Asignación por pestaña:

| Pestaña | Roles | Icono |
|---|---|---|
| Inicio | pública, entrenador, jugador | `home` |
| Torneos | pública, entrenador, jugador | `cuptrophy` |
| Equipos | entrenador | `people` |
| Reservar | jugador | `calendar` |
| Partidos | árbitro | `football` |
| Historial | árbitro | `history` |
| Perfil | entrenador, árbitro, jugador | `user` |

`size={22}` en la barra, frente a los 18 por defecto de las filas de menú: el área
táctil de una pestaña es mayor y el icono queda pequeño a 18.

### Cambios por pantalla

- **`TorneosScreen`** — el `🏆` vive dentro de `<Text style={ls.iconText}>` en un
  círculo verde (`ls.iconCircle`). Se sustituye por
  `<Icono nombre="cuptrophy" size={18} color={lp.greenText} />`. El círculo no cambia;
  `ls.iconText` deja de usarse ahí pero **no se borra del tema** sin comprobar antes
  que nadie más lo usa.

- **`PlayerHomeScreen`** — hoy el emoji va pegado al texto en el mismo `<Text>`
  (`"📊 Ver mis estadísticas"`). Los dos botones pasan a fila:
  `flexDirection: "row", alignItems: "center", gap: 8`, con el icono como hermano del
  texto. `📊` → `chart`, `📅` → `calendar`. El color sigue al del texto de cada botón
  (`btn.primaryText` y `btn.ghostText`).

- **`CoachHomeScreen`** — el array `ACCIONES` cambia `icon: "👥"` por
  `icono: "people"`, y el render sustituye `<Text style={cs.gridIcon}>` por
  `<Icono nombre={a.icono} size={24} color={lp.gold} />`. Mapeo: `👥`→`people`,
  `📝`→`docadd`, `📋`→`clipboardlist`, `📅`→`calendar`.

- **`ReservarScreen`** — el único cambio estructural. El `📍` está dentro del
  `placeholder`, que es un string y no admite un componente. El contenedor del
  buscador pasa a `flexDirection: "row", alignItems: "center", gap: 10`, con
  `<Icono nombre="location" size={18} color={lp.textMuted} />` a la izquierda y el
  `TextInput` con `flex: 1`. El placeholder queda `"Buscar sede"`, sin emoji.

## Flujo de datos

Ninguno nuevo. `Icono` es presentacional puro y los cambios son de render. Ninguna
pantalla cambia qué pide al API. La barra de navegación recibe el `color` de
React Navigation, que ya está configurado en los `screenOptions` de los cuatro
navegadores y no se toca.

## Manejo de errores

Sin cambios. Un `nombre` desconocido en `Icono` degrada a hueco vacío en vez de
lanzar, igual que hoy. El riesgo real es una **errata en un nombre**: no produce
error, produce un hueco invisible. Por eso `verificar-iconos.cjs` valida el
conjunto exacto de claves, y la validación en dispositivo recorre las cuatro barras.

## Verificación

Igual que en el PR #21, y con el mismo límite conocido:

1. `npm run verificar` sobre cada archivo tocado (usa el `@babel/core` del proyecto;
   **nunca `npx babel`**, que resuelve a un paquete v6 deprecado del caché de npx y
   da falsos negativos).
2. `npm run verificar-iconos` con la lista ampliada a dieciséis.
3. Suite de Python completa — debe seguir en **233**. No se toca `api/` ni `web/`,
   así que cualquier cambio ahí sería una señal de alarma. Tarda **~12,5 minutos**,
   no los 4 que estimaban notas viejas.
4. **Validación en dispositivo con Expo Go**, con checklist escrito. Es la única
   comprobación que prueba que los SVG renderizan y que ninguna pestaña quedó con un
   hueco por una errata.

No hay runner de tests JS en el proyecto: nada cubre `mobile/`. Un defecto que solo
se manifieste en ejecución no lo detecta ninguna de las tres primeras.

## Riesgos

- **Erratas en los nombres de icono.** Once claves nuevas repartidas por cuatro
  barras y cuatro pantallas. Una errata da un hueco invisible, no un error. Es el
  fallo más probable de la tanda y por eso el checklist recorre pestaña por pestaña.
- **Transcripción de paths SVG.** Los cinco del macro web se copian dentro del mismo
  repo, así que son verificables por comparación; los seis de Reicon se extraen a
  mano, como en el PR #21.
- **`calendar` y `people` traen 7 y 6 paths.** Son los más largos del lote y los más
  expuestos a que se pierda uno al copiar. Un path perdido no da error: da un icono
  incompleto. Conviene contar los paths de cada entrada nueva contra la tabla de
  arriba antes de dar la transcripción por buena.
- **Alto de la barra de navegación.** Añadir un icono de 22 px sobre la etiqueta
  puede empujar el alto de la barra en pantallas pequeñas. React Navigation lo
  gestiona solo, pero es lo segundo a mirar en el dispositivo.
