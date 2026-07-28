# Iconos vectoriales y menú de perfil unificado (móvil)

Fecha: 2026-07-27
Estado: aprobado por el usuario, pendiente de plan de implementación

## Problema

Dos cosas, relacionadas por la pantalla que tocan:

1. El menú de "Mi perfil" del jugador usa **emojis como iconos** (`✎ 💳 🔒 ⊗`), igual
   que la campanita de notificaciones de la cabecera de INICIO (`🔔`). Los emojis se
   renderizan con la fuente del sistema: cambian de forma entre Android e iOS, no
   heredan el color del tema y desentonan con el panel web, que desde el PR #18 usa
   SVG de [Reicon](https://reicon.dev) (MIT).
2. Entrenadores y árbitros **no tienen ese menú**. Comparten una pantalla de perfil
   distinta y más pobre: una pila de botones fantasma sin cabecera de avatar, sin
   insignia de rol y sin acceso a editar sus datos personales.

## Alcance

**Dentro:**
- Las 4 filas del menú de perfil (`✎ 💳 🔒 ⊗`) en los tres roles.
- La campanita `🔔` de la cabecera de INICIO del jugador.
- Llevar el menú de perfil del jugador a entrenador y árbitro.

**Fuera** (queda para otra tanda, decisión explícita del usuario):
- `NotificationsScreen` — `⚽ 🏆 🔔` por tipo de aviso y la `✕` de descartar.
- `PlayerHomeScreen` — `📊 📅` de los botones de acceso.
- `CoachHomeScreen` — `👥 📝 📋 📅` de la rejilla.
- `HomeScreen` — `📨`.
- `RefLiveScreen`, `RefSummaryScreen`, `LineupPitch` — `⚽ 🟨 🟥 🔁 ↑ ↓` de eventos.

**Fuera también:** ningún cambio en `api/` ni en `web/`. No se añaden endpoints.

## Decisiones tomadas

| Decisión | Elegido | Por qué |
|---|---|---|
| Motor de iconos | Reicon + `react-native-svg` | Paridad visual real con el panel web. La alternativa (`@expo/vector-icons`, ya instalado, cero dependencias) usa formas Feather/Ionicons, parecidas pero distintas. |
| Versión de `react-native-svg` | `15.2.0` vía `npx expo install` | Es la versión exacta que fija el SDK 51. Funciona en Expo Go sin build nativo. |
| Contenido del perfil de entrenador/árbitro | Las mismas 4 filas, **sin** cajas de estadísticas | No existe endpoint de stats agregadas para esos roles (solo `/jugador/estadisticas` y `/equipos/{id}/estadisticas`). Añadirlas habría llevado el trabajo al backend. |
| "Métodos de pago" para árbitro | Se conserva | `crear_reserva` y `crear_inscripcion` usan `get_current_user` sin restricción de rol: cualquier usuario autenticado puede reservar cancha. Sigue siendo un stub "Disponible próximamente" en los tres roles. |
| Correo en el perfil de entrenador/árbitro | Se conserva como texto atenuado | Hoy lo muestran. La insignia de rol sustituye a la fila "Rol", pero quitar el correo sería perder información. Asimetría deliberada: el perfil del jugador nunca lo mostró y sigue sin mostrarlo. |
| Ubicación de `PerfilScreen` | Se mueve a `src/screens/` | Hoy vive en `src/screens/coach/` pero `RefereeTabs` también la monta. La ruta induce a error. |

## Arquitectura

### `src/components/Icono.js` — nuevo

Espejo del macro `icono()` de `web/app/templates/_iconos.html`, adaptado a React
Native. La web guarda markup SVG crudo en un dict de Jinja; RN necesita elementos
`<Path>` reales, así que este módulo guarda **un array de descriptores de path por
icono**:

```js
const ICONOS = {
  edit:       [ { d: "…", stroke: true }, … ],
  creditcard: [ { d: "…" }, … ],
  lock:       [ … ],
  logout:     [ … ],
  bell:       [ … ],
};

export default function Icono({ nombre, size = 18, color = lp.textDark }) { … }
```

Contrato:
- `nombre` — clave de `ICONOS`. Un nombre desconocido renderiza un `<Svg/>` vacío del
  tamaño pedido, nunca revienta (mismo comportamiento que `_REICON.get(nombre, "")`
  en la web).
- `size` — lado en px, por defecto 18. `viewBox` siempre `0 0 24 24`.
- `color` — se aplica a `fill` o a `stroke` según el descriptor, que es como
  `currentColor` se comporta en la web.

Componente puro, sin estado ni efectos.

### Iconos a extraer

Del paquete npm `reicon@1.1.103`, descargado a un directorio de scratchpad — **nunca
a `node_modules` del proyecto**, igual que en el PR #18.

| Clave | Origen | Sustituye a |
|---|---|---|
| `edit` | `Edit2` | `✎` Editar datos personales |
| `creditcard` | ya presente en el macro web | `💳` Métodos de pago |
| `lock` | `Lock` | `🔒` Cambiar contraseña |
| `logout` | `Logout` | `⊗` Cerrar sesión |
| `bell` | `Bell` | `🔔` campanita de la cabecera |

### Piezas compartidas — nuevas

`PlayerProfileScreen` y `PerfilScreen` duplican hoy ~45 líneas idénticas de subir y
quitar foto, y ambas se reescriben en este trabajo. Se extrae solo lo que las dos
necesitan igual:

- **`src/components/OpcionMenu.js`** — la fila de menú (icono · texto · chevron `›`).
  Props: `icono`, `texto`, `onPress`, `color`. Hoy es una función privada `Opcion`
  dentro de `PlayerProfileScreen`.
- **`src/components/EditarPerfilModal.js`** — el modal de nombre/teléfono contra
  `PUT /auth/me`. Lo estrenan entrenador y árbitro sin copiarlo.
- **`src/hooks/useFotoPerfil.js`** — `cambiarFoto`, `quitarFoto`, `fotoV`, `subiendo`.
  Devuelve `fotoV` para el prop `version` del `Avatar` (el cache-busting del PR #20).

Es traslado de código, no cambio de lógica. Se justifica porque ambas pantallas se
reescriben de todos modos; no es una refactorización aparte.

### `src/screens/PerfilScreen.js` — movida y reescrita

Movida desde `src/screens/coach/PerfilScreen.js`. Estructura nueva, calcada de la del
jugador:

```
         (avatar)
     Demo entrenador
      [ENTRENADOR]
    correo@demo.com          <- atenuado, solo entrenador/árbitro
 [Cambiar foto] [Quitar foto]

  ✎  Editar datos personales   ›
  ▤  Métodos de pago           ›
  ○  Cambiar contraseña        ›
  ⊗  Cerrar sesión             ›
```

El acento sale de `usuario.rol`: `lp.gold` para `entrenador`, `lp.maroon` para
`arbitro`. Las cabeceras de navegación de `App.js` no se tocan.

Desaparece la fila "Rol" (la sustituye la insignia). Aparece "Editar datos
personales", que estos roles no tenían.

### Cambios puntuales

- **`src/screens/player/PlayerProfileScreen.js`** — las 4 cadenas de emoji pasan a
  `<Icono>`; consume `OpcionMenu`, `EditarPerfilModal` y `useFotoPerfil` compartidos.
  Su layout, sus cajas GOLES/PARTIDOS y su comportamiento no cambian.
- **`src/screens/player/PlayerHomeScreen.js`** — `Campanita` cambia `🔔` por
  `<Icono nombre="bell" size={20} color={lp.white} />`. El punto rojo de "hay nuevas"
  se queda tal cual.
- **`App.js`** — se actualiza la ruta del import de `PerfilScreen`.
- **`mobile/package.json`** — entra `react-native-svg` `~15.2.0`.

## Flujo de datos

`Icono` y `OpcionMenu` son presentacionales puros. `EditarPerfilModal` recibe los
valores iniciales por props y devuelve el usuario actualizado por callback; el
`PUT /auth/me` lo hace el modal. `useFotoPerfil` encapsula `subirFoto`/`borrarFoto`
de `api.js` y llama a `refrescar()` de `useAuth` tras cada operación, como hoy.

`useAuth().usuario` es el `UsuarioOut` completo que devuelve `/auth/me` — incluye
`nombre`, `correo`, `rol` y `telefono`. Por tanto **el modal no pide nada al montar**:
entrenador y árbitro le pasan `usuario.nombre` y `usuario.telefono` directamente. El
jugador le pasa los de su estado `me`, que ya carga hoy junto a sus estadísticas.

Ninguna pantalla cambia qué pide al API, salvo entrenador y árbitro, que estrenan
`PUT /auth/me` — un endpoint que ya existe y no restringe rol.

## Manejo de errores

Sin cambios respecto a hoy: los fallos de subida y borrado de foto siguen saliendo
por `Alert.alert` con el mensaje del servidor. Un `nombre` desconocido en `Icono`
degrada a hueco vacío en vez de romper el render.

**Nota:** `subirFoto` sigue sin timeout (follow-up (h) del ledger de PR #20). Este
trabajo no lo arregla y no lo empeora; queda donde está.

## Verificación

El proyecto **no tiene runner de tests JS**. Los 233 tests son de Python y no cubren
nada de `mobile/`. La verificación será, en este orden:

1. **Parseo con babel** de cada archivo tocado (el método del PR #20).
2. **Suite de Python completa** — debe seguir en 233 en verde. No se toca `api/` ni
   `web/`, así que cualquier cambio ahí sería una señal de alarma.
3. **Validación en dispositivo con Expo Go**, con checklist escrito. Es la única
   comprobación que prueba de verdad que los SVG renderizan, que los tres roles ven
   su menú y que la campanita sigue mostrando el punto rojo.

Límite conocido y aceptado: los dos bugs del PR #20 (el `Authorization` poco fiable
de `<Image>` en RN, el z-index de la foto en la web) se escaparon a la verificación
estática. Con SVG el riesgo es menor — no hay red ni autenticación de por medio —
pero el trabajo no se declara probado hasta la validación en dispositivo.

## Riesgos

- **`react-native-svg` en Expo Go.** Está en el SDK 51 y `npx expo install` fija la
  versión compatible, así que no hace falta build personalizado. Si aun así fallara
  el render en Expo Go, el plan B es `@expo/vector-icons` (ya instalado), aceptando
  formas distintas a las de la web.
- **Mover `PerfilScreen`.** Solo `App.js` la importa; el riesgo es un import huérfano,
  que el parseo con babel y el arranque de Expo detectan de inmediato.
