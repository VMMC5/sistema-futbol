# Manual de Interfaces — App móvil "Torneos"

> Documento de sistema de diseño listo para **Zeroheight**. Reúne los fundamentos
> visuales (color, tipografía, iconografía) y el catálogo de **31 pantallas** de la
> app React Native, con su objetivo y funciones.
>
> **App:** Torneos v1.0.0 · **Stack:** React Native + Expo (SDK 51) · React Navigation
> (native-stack + bottom-tabs) · Autenticación con `expo-secure-store`.
> **Fuente de verdad:** `mobile/src/` (temas en `theme.js` y `publicTheme.js`, navegación en `App.js`).
>
> 📷 Las capturas se indican con un marcador de imagen en cada pantalla — súbelas en Zeroheight.

---

## 1. Paleta de colores

La app usa **dos paletas** según el contexto:

### 1.1 Paleta "Cancha" (oscura) — pantallas de cuenta/acceso
Definida en `theme.js`. Fondo verde muy oscuro con acento lima, evoca una cancha nocturna.

| Token | Hex / valor | Uso |
|-------|-------------|-----|
| `pitch900` | `#07140D` | Fondo de pantalla y de inputs |
| `pitch800` | `#0B2014` | Cabeceras (header oscuro) |
| `pitch700` | `#0F2C1B` | Fondo de tarjetas |
| `pitch600` | `#163D26` | Superficies elevadas |
| `line` | `rgba(198,255,0,0.16)` | Bordes sutiles (lima translúcido) |
| `lime` | `#C6FF2E` | Acento / botón primario / marcadores |
| `chalk` | `#EAF3EC` | Texto principal |
| `muted` | `#8AA595` | Texto secundario / labels |
| `danger` | `#FF5A5A` | Errores |

### 1.2 Paleta "Clara" (pública y paneles por rol)
Definida en `publicTheme.js`. Fondo crema, tarjetas verde oscuro, acentos por rol.

| Token | Hex | Uso |
|-------|-----|-----|
| `bg` | `#EDEAE1` | Fondo de pantalla (crema) |
| `surface` | `#FBFAF6` | Filas / tarjetas claras |
| `surfaceBorder` | `#E3DFD3` | Bordes de superficies |
| `green` | `#123D2A` | Tarjetas "feature" · **cabecera del Jugador** |
| `greenText` | `#F2F0E8` | Texto sobre verde |
| `accent` | `#2E7D52` | Pestañas/badges activos, rankings |
| `textDark` | `#1A2A20` | Texto principal |
| `textMuted` | `#7C887E` | Texto secundario |
| `white` | `#FFFFFF` | Texto sobre acento |
| `gold` | `#8A6D1E` | **Cabecera y tarjeta del Entrenador** |
| `goldText` | `#F7F1DF` | Texto sobre dorado |
| `maroon` | `#7C2B2B` | **Cabecera del Árbitro** |
| `red` | `#C0392B` | Botones principales del Árbitro |
| `danger` | `#C0392B` | Errores |

### 1.3 Color por rol (identidad de cada panel)
Cada rol tiene un color de cabecera que lo identifica:

| Área | Color de cabecera | Texto |
|------|-------------------|-------|
| Público | `#EDEAE1` (crema) | `#1A2A20` oscuro |
| Cuenta / acceso | `#0B2014` (verde oscuro "cancha") | `#EAF3EC` |
| **Jugador** | `#123D2A` (verde) | blanco |
| **Entrenador** | `#8A6D1E` (dorado) | `#F7F1DF` |
| **Árbitro** | `#7C2B2B` (guinda) | blanco |

---

## 2. Tipografía

- **Familia:** fuente **del sistema** (San Francisco en iOS, Roboto en Android). No se cargan fuentes personalizadas (`useFonts`/`expo-font` no se usan).
- **Pesos:** `600` (semibold), `700` (bold), `800` (extrabold). Los títulos y etiquetas casi siempre en `800`.
- **Recursos de estilo:** `letterSpacing` (0.5–1.5) y `textTransform: uppercase` en títulos de sección y cabeceras.

### Escala tipográfica

| Estilo | Tamaño | Peso | Notas |
|--------|--------|------|-------|
| `h1` | 28 | 800 | Títulos de pantalla (acceso), `letterSpacing 0.5` |
| `h2` | 20 | 800 | Subtítulos de sección |
| `featureGoldName` | 20 | 800 | Nombre destacado (tarjeta dorada del entrenador) |
| `statNum` | 24 | 800 | Números grandes de estadísticas |
| `score` | 22 | 800 | Marcador (color lima) |
| `cardTitle` / `rowTitle` | 15–16 | 700 | Títulos de tarjeta/fila |
| `infoValue` | 16 | 700 | Valores de detalle |
| `btnText` | 15 | 800 | Texto de botón |
| Cuerpo / `muted` | 13–14 | 400–600 | Texto secundario |
| `sectionTitle` | 13 | 800 | Uppercase, `letterSpacing 1` |
| `badge` / `pill` | 11–12 | 700–800 | Etiquetas de estado |

---

## 3. Iconografía

La app **no usa una librería de iconos** (no hay `@expo/vector-icons` ni SVG). La
iconografía se resuelve con **emoji** y **caracteres tipográficos**, lo que la hace
ligera y sin dependencias.

### 3.1 Emoji funcionales

| Icono | Significado |
|-------|-------------|
| ⚽ | Gol / fútbol |
| 🟨 | Tarjeta amarilla |
| 🟥 | Tarjeta roja |
| 🔁 | Cambio de jugador |
| 🏆 | Torneo / campeonato |
| 👥 | Equipo / jugadores |
| 📅 | Calendario / partidos |
| 📋 | Alineación / acta |
| 📝 | Registro / formulario |
| 💳 | Pago / métodos de pago |
| 🔔 | Notificaciones (campanita) |
| 🔒 | Contraseña / seguridad |
| 📍 | Ubicación / buscar sede |

### 3.2 Iconos tipográficos (caracteres)

| Carácter | Uso |
|----------|-----|
| `✎` | Editar |
| `⊗` | Quitar / eliminar |
| `›` (chevron) | Navegar al detalle (`cs.chevron`, 22px) |
| `✓` | Confirmado (ej. "acta enviada ✓") |

### 3.3 Patrones de icono
- **Punto de pestaña (`Punto`)**: indicador de 6px en la barra inferior; `accent` (#2E7D52) cuando está activa, `#C7C2B5` inactiva.
- **Círculo de icono (`iconCircle` / `avatar`)**: 40–42px, fondo verde/color, contiene emoji o iniciales (avatar de jugador con iniciales en `avatarText`).

---

## 4. Componentes base

Reutilizados en toda la app (definidos en `styles`, `ls`, `cs`):

- **Tarjeta (`card` / `row` / `feature`)**: contenedor con borde y radio 12–14.
- **Botón primario (`btn` / `primaryBtn`)**: relleno lima (oscuro) o dorado (entrenador), texto 800.
- **Botón fantasma (`btnGhost` / `ghostBtn`)**: solo borde.
- **Input (`input` / `smallInput`)**: campo con borde y radio 10, más `label`.
- **Pill / Badge (`pill`, `badge`, `badgeOn`, `badgeNext`)**: etiquetas de estado ("ACTIVO", "PRÓXIMO").
- **Pestañas internas (`tabs`)**: segmentación tipo toggle (ej. Tabla/Partidos/Goleo).
- **Fila de posiciones (`standRow`)**: ranking + equipo + puntos.
- **Caja de estadística (`statBox` / `statNum` / `statLabel`)**: KPI numérico.
- **Grid de accesos (`grid` / `gridItem`)**: cuadrícula 2 columnas con emoji + etiqueta.

---

## 5. Sistema de navegación

Un **Stack** raíz contiene áreas con **pestañas inferiores** (bottom-tabs) por rol.
Al entrar, cada usuario va a su panel según su rol (`rutaPanel`). Desde el área
pública, un botón "Ingresar / Mi panel" en la cabecera lleva al acceso o al panel.

| Área | Pestañas inferiores |
|------|---------------------|
| Público | Inicio · Torneos |
| Jugador | Inicio · Torneos · Reservar · Perfil |
| Entrenador | Inicio · Equipos · Torneos · Perfil |
| Árbitro | Partidos · Historial · Perfil |

---

# 6. Catálogo de interfaces

> Cada ficha: **ruta** (nombre en el navegador) · **cabecera** (color) · objetivo · funciones.
> 📷 = marcador para la captura del móvil.

## 6.1 Cuenta y acceso · tema "Cancha" (oscuro)

### Iniciar sesión — `Login`
📷 `![Login](capturas/login.png)`
**Objetivo:** que un usuario acceda a su panel con correo y contraseña.
**Funciones:** validar credenciales; enlaces a "Crear cuenta" (jugador) y "Entrenador/Árbitro"; al entrar, redirige al panel según el rol.

### Crear cuenta de jugador — `RegisterPlayer`
📷 `![RegisterPlayer](capturas/register-player.png)`
**Objetivo:** auto-registro estándar de un **jugador**.
**Funciones:** captura de nombre, correo, contraseña y datos básicos; crea la cuenta y deja al usuario listo para iniciar sesión.

### Solicitud Entrenador / Árbitro — `RegisterStaff`
📷 `![RegisterStaff](capturas/register-staff.png)`
**Objetivo:** solicitar alta como **entrenador o árbitro** (requiere aprobación).
**Funciones:** datos + teléfono opcional; **subida de un documento** (PDF o imagen, vía `expo-document-picker`) que el administrador revisará antes de aprobar.

### Cambiar contraseña (primer ingreso) — `ChangePassword`
📷 `![ChangePassword](capturas/change-password.png)`
**Objetivo:** cambio **obligatorio** de contraseña en el primer ingreso de entrenadores/árbitros que entraron con la contraseña temporal del correo.
**Funciones:** pedir la temporal + la nueva; actualizarla y liberar el acceso al panel.

### Mi panel (post-login) — `Home`
📷 `![Home](capturas/home.png)`
**Objetivo:** punto de entrada tras iniciar sesión; muestra contenido según el rol.
**Funciones:** saludo con el nombre del usuario y accesos a su panel correspondiente.

## 6.2 Público · tema claro (crema)

### Inicio (público) — `Inicio`
📷 `![Inicio](capturas/publico-inicio.png)`
**Objetivo:** vitrina de **próximos partidos** para cualquier visitante (sin sesión).
**Funciones:** lista de partidos próximos; botón "Ingresar" en la cabecera.

### Torneos (público) — `Torneos`
📷 `![Torneos](capturas/publico-torneos.png)`
**Objetivo:** explorar torneos **activos** y **próximos**.
**Funciones:** pestañas Activos/Próximos; cada torneo abre su detalle (estadísticas o info).

### Detalle de torneo en curso — `TorneoStats`
📷 `![TorneoStats](capturas/torneo-stats.png)`
**Objetivo:** ver un torneo **en curso**.
**Funciones:** pestañas **Tabla** (posiciones), **Partidos** (resultados/calendario) y **Goleo** (tabla de goleadores).

### Detalle de torneo próximo — `TorneoInfo`
📷 `![TorneoInfo](capturas/torneo-info.png)`
**Objetivo:** información de un torneo **próximo a empezar**.
**Funciones:** datos de inscripción (fechas, sede, costo) en filas de detalle.

## 6.3 Jugador · cabecera verde `#123D2A`

### Inicio del jugador — `PlayerHome`
📷 `![PlayerHome](capturas/player-home.png)`
**Objetivo:** panel de bienvenida del jugador.
**Funciones:** tarjeta de bienvenida; "tu próximo partido"; accesos a estadísticas y próximos partidos; **campanita 🔔** de notificaciones en la cabecera.

### Mi perfil — `PlayerProfile`
📷 `![PlayerProfile](capturas/player-profile.png)`
**Objetivo:** perfil del jugador.
**Funciones:** avatar con iniciales, datos y cajas de stats; accesos a editar datos, **métodos de pago (próximamente)**, cambiar contraseña y cerrar sesión.

### Mis estadísticas — `PlayerStats`
📷 `![PlayerStats](capturas/player-stats.png)`
**Objetivo:** rendimiento personal del jugador.
**Funciones:** cajas de goles/asistencias/amarillas; **gráfica de goles por jornada**; minutos jugados; filtro por torneo.

### Próximos partidos — `PlayerCalendar`
📷 `![PlayerCalendar](capturas/player-calendar.png)`
**Objetivo:** ver el calendario de partidos del jugador.
**Funciones:** **calendario mensual** con los días de partido marcados y la lista de partidos debajo.

### Notificaciones — `Notifications`
📷 `![Notifications](capturas/notifications.png)`
**Objetivo:** bandeja de avisos e invitaciones del jugador.
**Funciones:** invitaciones a equipo con **Aceptar/Rechazar**; avisos con opción de eliminar; al abrir, marca los avisos como leídos.

### Invitaciones — `Invitations`
📷 `![Invitations](capturas/invitations.png)`
**Objetivo:** bandeja específica de invitaciones a equipo.
**Funciones:** listar invitaciones pendientes y **Aceptar/Rechazar**.

### Reservar cancha — `Reservar`
📷 `![Reservar](capturas/reservar.png)`
**Objetivo:** reservar una cancha.
**Funciones:** **📍 buscar sede**, elegir una de sus canchas, fecha y horario (los horarios ocupados se deshabilitan).

### Pago — `Pago`
📷 `![Pago](capturas/pago.png)`
**Objetivo:** pantalla de pago reutilizable para **reservas e inscripciones**.
**Funciones:** flujo de pago con estilos autocontenidos; al confirmar, dirige al comprobante.

### Comprobante — `Comprobante`
📷 `![Comprobante](capturas/comprobante.png)`
**Objetivo:** mostrar el comprobante de un pago.
**Funciones:** resumen del pago y **descargar PDF** (vía `expo-file-system` + `expo-sharing`).

## 6.4 Entrenador · cabecera dorada `#8A6D1E`

### Inicio del entrenador — `CoachHome`
📷 `![CoachHome](capturas/coach-home.png)`
**Objetivo:** panel principal del entrenador.
**Funciones:** tarjeta dorada de su equipo; accesos rápidos (grid con emoji); "próximo partido"; si no tiene equipo, invita a "crear tu primer equipo".

### Mis equipos — `TeamList`
📷 `![TeamList](capturas/team-list.png)`
**Objetivo:** listar los equipos del entrenador.
**Funciones:** ver equipos y entrar a editar cada uno.

### Crear / editar equipo — `TeamEdit`
📷 `![TeamEdit](capturas/team-edit.png)`
**Objetivo:** gestionar un equipo y su plantilla.
**Funciones:** la plantilla se construye por **invitaciones** (no se teclea): ver miembros, editar dorsal/posición o quitar (`✎`/`⊗`), e invitar jugadores.

### Estadísticas del equipo — `TeamStats`
📷 `![TeamStats](capturas/team-stats.png)`
**Objetivo:** rendimiento del equipo.
**Funciones:** récord (V/E/D), posición en liga y goleadores.

### Elegir partido para alineación — `LineupMatches`
📷 `![LineupMatches](capturas/lineup-matches.png)`
**Objetivo:** elegir a qué próximo partido definir la alineación.
**Funciones:** lista de próximos partidos del entrenador.

### Definir alineación — `Lineup`
📷 `![Lineup](capturas/lineup.png)`
**Objetivo:** armar la alineación de un partido.
**Funciones:** elegir **formación** y colocar a los jugadores de la plantilla sobre la cancha; quitar de posición; guardar el plan en el backend.

### Invitar jugadores — `InvitePlayers`
📷 `![InvitePlayers](capturas/invite-players.png)`
**Objetivo:** sumar jugadores al equipo.
**Funciones:** buscar jugadores registrados **sin equipo** e invitarlos.

### Perfil (entrenador/árbitro) — `Perfil`
📷 `![Perfil](capturas/perfil.png)`
**Objetivo:** perfil del usuario autenticado (compartido por entrenador y árbitro).
**Funciones:** datos, cambiar contraseña y cerrar sesión.

## 6.5 Árbitro · cabecera guinda `#7C2B2B`

### Partidos asignados — `RefMatches`
📷 `![RefMatches](capturas/ref-matches.png)`
**Objetivo:** ver los partidos asignados al árbitro (programados y en juego).
**Funciones:** lista de asignaciones; el botón **"Iniciar"** se desbloquea solo cuando llega la fecha/hora.

### Historial — `RefHistory`
📷 `![RefHistory](capturas/ref-history.png)`
**Objetivo:** consultar los partidos ya dirigidos.
**Funciones:** lista de partidos finalizados con acceso a su acta/resumen.

### Partido en vivo — `RefLive`
📷 `![RefLive](capturas/ref-live.png)`
**Objetivo:** dirigir un partido en tiempo real.
**Funciones:** marcador; botones de eventos (**⚽ gol / 🟨 amarilla / 🟥 roja / 🔁 cambio**); caja con los eventos registrados; botón de finalizar; acceso a "ver acta".

### Registrar evento — `RefEvent`
📷 `![RefEvent](capturas/ref-event.png)`
**Objetivo:** capturar el detalle de un evento del partido.
**Funciones:** muestra las alineaciones y, según el tipo, pide **anotador + asistencia + subtipo** (gol), **jugador** (tarjeta) o **sale + entra** (cambio).

### Resumen del partido (acta) — `RefSummary`
📷 `![RefSummary](capturas/ref-summary.png)`
**Objetivo:** cerrar el partido con el acta oficial.
**Funciones:** marcador final, goles, tarjetas, **firma digital** y **envío del acta** al sistema.

---

## Apéndice — Índice de pantallas (31)

| # | Área | Ruta | Título de cabecera |
|---|------|------|--------------------|
| 1 | Acceso | Login | Ingresar |
| 2 | Acceso | RegisterPlayer | Crear cuenta |
| 3 | Acceso | RegisterStaff | Entrenador / Árbitro |
| 4 | Acceso | ChangePassword | Cambiar contraseña |
| 5 | Acceso | Home | Mi panel |
| 6 | Público | Inicio | INICIO |
| 7 | Público | Torneos | TORNEOS |
| 8 | Público | TorneoStats | TORNEO |
| 9 | Público | TorneoInfo | TORNEO |
| 10 | Jugador | PlayerHome | INICIO |
| 11 | Jugador | PlayerProfile | MI PERFIL |
| 12 | Jugador | PlayerStats | MIS ESTADÍSTICAS |
| 13 | Jugador | PlayerCalendar | PRÓXIMOS PARTIDOS |
| 14 | Jugador | Notifications | NOTIFICACIONES |
| 15 | Jugador | Invitations | Invitaciones |
| 16 | Jugador | Reservar | RESERVAR CANCHA |
| 17 | Jugador | Pago | PAGO |
| 18 | Jugador | Comprobante | COMPROBANTE |
| 19 | Entrenador | CoachHome | INICIO |
| 20 | Entrenador | TeamList | MIS EQUIPOS |
| 21 | Entrenador | TeamEdit | EQUIPO |
| 22 | Entrenador | TeamStats | ESTADÍSTICAS |
| 23 | Entrenador | LineupMatches | ALINEACIÓN |
| 24 | Entrenador | Lineup | ALINEACIÓN |
| 25 | Entrenador | InvitePlayers | INVITAR |
| 26 | Entrenador/Árbitro | Perfil | PERFIL |
| 27 | Árbitro | RefMatches | PARTIDOS ASIGNADOS |
| 28 | Árbitro | RefHistory | HISTORIAL |
| 29 | Árbitro | RefLive | PARTIDO EN VIVO |
| 30 | Árbitro | RefEvent | EVENTO |
| 31 | Árbitro | RefSummary | RESUMEN DEL PARTIDO |
