# Fotos de perfil y alineaciones visuales — diseño

Fecha: 2026-07-22
Estado: aprobado (diseño visual), pendiente de revisión del spec.

## Objetivo

Que jugadores, entrenadores y árbitros suban una foto de perfil, y que esa foto
sirva para identificarlos en las alineaciones, en tres sitios:

1. **Móvil — LineupScreen** (entrenador): la cancha donde arma su alineación, ya
   existente; solo hay que meter la foto en cada hueco.
2. **Web — detalle del partido**: hoy dice «Sin alineación registrada»; pasa a
   mostrar ambos equipos en una cancha completa con fotos, eventos y banca.
3. **Móvil — vista del árbitro**: una cancha por equipo con pestañas, con las
   fotos, reutilizando el mismo componente conceptual que el panel web.

No es un objetivo: cobro, moderación automática de contenido, ni recorte
interactivo de la foto por el usuario (se recorta en el servidor, centrado).

## Contexto que condiciona el diseño

- **`Usuario` no tiene columna de foto.** Hay que añadirla (migración).
- **Existe un patrón de subida reutilizable** en `api/app/routers/solicitudes.py`:
  UUID como nombre, whitelist de `content_type`, límite de 5 MB, guardado en
  `UPLOAD_DIR`, y servido con un endpoint protegido + `FileResponse`. El panel
  web lo proxea con su sesión (`web/app/app.py` → `/solicitudes/<id>/documento`).
- **Dos tablas de alineación**, y una está muerta:
  - `alineaciones` (oficial del árbitro): **0 filas**, ninguna pantalla la
    escribe. Endpoints huérfanos.
  - `alineacion_planes` (el plan del entrenador): **2 filas**, es la real. Guarda
    `formacion` (texto) y `jugadores` (JSON con `jugador_equipo_id`, `jugador_id`,
    `nombre`, `dorsal`, `posicion`, `orden`). El endpoint `GET /partidos/{id}/plan`
    ya devuelve `jugadores` (titulares) **y** `suplentes` (resto de la plantilla).
  - **Decisión (ya tomada con el usuario):** el panel web pasa a leer el plan de
    ambos equipos. La tabla `alineaciones` se deja como está, sin tocar; su
    limpieza es un trabajo aparte, fuera de este spec.
- **El mapeo formación → posiciones ya existe** en `LineupScreen.js`:
  `FORMACIONES` (solo `4-4-2`, `4-3-3`, `3-5-2`) + `huecos()` devuelve coordenadas
  `(x, y)` en fracción 0..1. Es la fuente de verdad; se reutiliza, no se duplica.
- **`EventoPartido` ya guarda lo necesario para los distintivos**: `jugador_id`,
  `jugador_secundario_id` (asistente en un gol, o quien entra en un cambio),
  `tipo` (`gol`, `tarjeta_amarilla`, `tarjeta_roja`, `cambio`) y `subtipo`. Los
  distintivos se derivan agregando los eventos del partido; **no se toca el
  modelo de eventos**.
- **RefEventScreen** (árbitro) ya descarga los planes de ambos equipos y tiene un
  selector de equipo, pero pinta **listas verticales**, no cancha. Ahí sí hay una
  vista nueva.
- Pillow **no** está en `api/requirements.txt` (sí en `brand/generar-assets.py`,
  que corre aparte). Se añade al API para normalizar la foto al subirla.

## Decisiones de diseño (ya acordadas)

| Tema | Decisión |
|------|----------|
| Cómo se sirve la foto | Endpoint protegido con JWT (mismo patrón que el documento de solicitud). Web proxea; móvil manda el token en la cabecera de `<Image>`. |
| Quién sube | Cada usuario la suya. El superadmin solo puede **borrar** (moderación). Nadie sube la foto de otro. |
| Panel web — alineación | Maqueta A/v4: cancha completa 2:3, local arriba, visitante en espejo abajo, banca en dos columnas, eventos agrupados por tipo en la tarjeta del marcador, distintivos sobre cada jugador. |
| Árbitro | Maqueta C: una cancha por equipo con pestañas. |
| Equipo sin plan | Media cancha con su geometría intacta + aviso centrado «Alineación no registrada». |

## Arquitectura

Tres unidades con fronteras claras:

### Unidad 1 — Almacenamiento y servido de la foto (API)

**Modelo.** Nueva columna en `usuarios`:
```
foto_nombre = Column(String(255))   # NULL = sin foto; UUID+ext si tiene
```
Migración Alembic `add_foto_usuario` sobre `c2e3f4a5b6d7` (la última). Como los
tests construyen el esquema con `create_all`, la columna en el modelo basta para
ellos; la migración es para producción. (Ver [[migraciones-consolidadas-2026-07]]
para el estado del historial de Alembic.)

**Normalización.** Al subir, con Pillow: abrir, corregir orientación EXIF,
recortar al cuadrado centrado, redimensionar a 512×512, re-guardar como JPEG
(calidad ~85). Esto acota el tamaño en disco y unifica el formato, así que el
front nunca recibe una imagen de 4 MB ni una relación de aspecto rara. Se añade
`Pillow` a `api/requirements.txt`.

**Endpoints** (router `usuarios`):
- `POST /usuarios/me/foto` — el usuario autenticado sube/reemplaza la suya.
  Multipart `foto: UploadFile`. Valida `content_type` (solo `image/png`,
  `image/jpeg`), luego lee el contenido y rechaza si supera 5 MB — igual que
  `solicitudes.py`, que lee entero y mide `len()` (con `UploadFile` no hay tamaño
  fiable antes de leer). Borra el archivo anterior si existía. Devuelve
  `UsuarioOut`. **Nota de ruta:** declarar `/me/foto` **antes** que
  `/{usuario_id}/foto` en el router, o FastAPI intentará parsear `"me"` como
  `usuario_id` (int) y dará 422.
- `DELETE /usuarios/me/foto` — el usuario borra la suya.
- `DELETE /usuarios/{id}/foto` — solo superadmin (moderación). Borra archivo y
  pone `foto_nombre = NULL`.
- `GET /usuarios/{id}/foto` — `Depends(get_current_user)`. Devuelve el `FileResponse`
  con `Cache-Control: private, max-age=3600` (una alineación pide hasta 22 fotos;
  la caché evita re-descargas en refrescos). 404 si el usuario no tiene foto.

**Almacenamiento en disco.** Reutiliza `UPLOAD_DIR`, en subcarpeta `fotos/`.
Nombre `{uuid}.jpg`. Mismo volumen que ya persiste las solicitudes.

**Esquema.** `UsuarioOut` y `UsuarioAdminOut` ganan `tiene_foto: bool`
(derivado de `foto_nombre is not None`). No se expone el nombre de archivo; el
front construye la URL como `/usuarios/{id}/foto` solo si `tiene_foto`. Los
`PlanItemOut` ya traen `jugador_id`, con el que se pide la foto.

**Autorización — por qué `GET` requiere solo estar logueado y no ser el dueño:**
una alineación la ven el rival, el árbitro y cualquiera con sesión en el panel;
restringir la foto al dueño rompería justo el caso de uso. El requisito del PI es
«API protegida con JWT», que se cumple: sin token no hay foto.

### Unidad 2 — Agregación de eventos por jugador (API)

Un helper nuevo, `resumen_eventos_por_jugador(db, partido_id)`, que recorre los
`EventoPartido` del partido y devuelve, por `jugador_id`:
```
{ jugador_id: {goles: int, asistencias: int, amarillas: int, rojas: int,
               salio: bool, entro: bool} }
```
Reglas de derivación:
- `gol` → +1 gol a `jugador_id`; si `jugador_secundario_id`, +1 asistencia a ese.
  (`subtipo == "autogol"` cuenta gol en contra; **no** suma al goleador — se
  excluye del distintivo de gol, coherente con `_equipo_que_anota` en
  `partidos.py`.)
- `tarjeta_amarilla` / `tarjeta_roja` → +1 a `jugador_id`.
- `cambio` → `jugador_id` marca `salio=True`; `jugador_secundario_id` marca
  `entro=True`.

Se expone en un endpoint nuevo `GET /partidos/{id}/resumen-jugadores` (o embebido
en el plan; ver «Preguntas abiertas»). Es de solo lectura y no depende del rol más
allá de estar autenticado.

### Unidad 3 — Las tres vistas

Un mismo modelo mental de «cancha» en dos plataformas. No comparten código (uno es
Jinja/CSS, el otro React Native), pero sí el **contrato de datos**: formación +
lista de titulares con `orden` + resumen de eventos por jugador.

**3a. Web — detalle del partido** (`web/app/templates/partido_detalle.html` +
`web/app/app.py` + `styles.css`):
- La ruta `partido_detalle` deja de pedir `/alineacion` y pide
  `/plan?equipo_id=local` y `/plan?equipo_id=visitante`, más
  `/resumen-jugadores`.
- Layout nuevo: tarjeta 1 = marcador + eventos agrupados por tipo (goles juntos
  con el balón, tarjetas juntas, cambios juntos), cada jugador del lado de su
  equipo. Tarjeta 2 = cancha 2:3 (SVG con líneas reglamentarias: áreas grande y
  chica, penal, arco, círculo central, córners, en ambas porterías), local arriba
  y visitante en espejo, distintivos sobre cada avatar, y banca en dos columnas
  debajo.
- Las coordenadas de cada línea de la formación se calculan en Python replicando
  la lógica de `huecos()` (líneas repartidas por % de altura, jugadores por % de
  ancho). Se documenta que la fuente canónica es `FORMACIONES` en el móvil.
- Equipo sin plan: media cancha con el aviso centrado, geometría intacta.
- Fotos vía `<img src="/usuarios/{id}/foto">` proxeado por Flask con la sesión
  (nueva ruta `/usuarios/<id>/foto` en `web/app/app.py`, como la del documento de
  solicitud). Fallback a un avatar con la inicial cuando `tiene_foto` es falso.
- CSP: cero JS nuevo, cero `style=` inline (se aprendió en PR #17). Los avatares
  y distintivos son clases CSS; la cancha es un SVG estático en el template.

**3b. Móvil — LineupScreen** (`mobile/src/screens/coach/LineupScreen.js`):
- Cada hueco de la cancha muestra la foto del jugador asignado (con token en la
  cabecera de `<Image>`), con fallback a la inicial. Es el cambio más pequeño:
  la cancha, los slots y el mapeo de formación ya existen.

**3c. Móvil — vista del árbitro** (nuevo componente `LineupPitch` +
`RefLineupScreen`, enganchado desde el flujo del árbitro):
- Componente `LineupPitch` reutilizable que dibuja **una** cancha (un equipo) con
  fotos y distintivos, alimentado por `plan` + `resumen-jugadores`.
- Pantalla con pestañas local/visitante que reutiliza el selector de equipo que
  RefEventScreen ya tiene. Cada pestaña renderiza `LineupPitch`.
- Se enlaza desde donde el árbitro inicia/gestiona el partido (RefLiveScreen o el
  menú del partido); punto de entrada exacto a definir en el plan.

## Flujo de datos

```
Subida:   usuario → POST /usuarios/me/foto → Pillow normaliza → UPLOAD_DIR/fotos/{uuid}.jpg
                                            → usuarios.foto_nombre = "{uuid}.jpg"

Lectura (alineación):
  cliente → GET /partidos/{id}/plan?equipo_id=local     → titulares + suplentes
          → GET /partidos/{id}/plan?equipo_id=visitante
          → GET /partidos/{id}/resumen-jugadores        → distintivos por jugador
  por cada jugador con tiene_foto:
          → GET /usuarios/{jugador_id}/foto (con JWT)    → imagen 512², cacheada 1h
```

## Manejo de errores

- Subir algo que no es imagen o >5 MB → 400 con mensaje claro (igual que el
  documento de solicitud).
- Pillow no puede abrir el archivo (imagen corrupta disfrazada de JPEG) → 400
  «No se pudo procesar la imagen», sin dejar rastro en disco.
- `GET /usuarios/{id}/foto` de un usuario sin foto → 404; el front ya no la pide
  porque `tiene_foto` es falso, pero el endpoint es defensivo.
- Archivo en la BD pero borrado del disco → 404 (mismo patrón que el documento).
- Plan inexistente para un equipo → el endpoint del plan ya devuelve titulares
  vacíos; la vista muestra el aviso «Alineación no registrada».

## Pruebas

- **API foto**: subir JPG/PNG válido (201 + `tiene_foto`), reemplazar (borra el
  anterior), subir no-imagen (400), subir >5 MB (400), borrar la propia (200),
  borrar ajena como no-admin (403), borrar ajena como admin (200), GET sin token
  (401), GET de usuario sin foto (404). Verificar que Pillow deja 512×512 JPEG.
- **API resumen**: partido con gol+asistencia, doblete, autogol (no cuenta al
  goleador), amarilla, roja, cambio (salió/entró) → agregados correctos.
- **Web**: el detalle del partido con dos planes muestra ambas canchas; con un
  solo plan muestra el aviso en la mitad correcta; proxy de foto responde con la
  sesión. (Los tests de web hoy son mínimos; al menos un render que no rompa.)
- **Móvil**: fuera del alcance de pytest; validación manual con Expo (checklist
  en el plan).

## Decisiones sobre las preguntas abiertas (resueltas con el usuario 2026-07-22)

1. **`resumen-jugadores` es un endpoint aparte**, `GET /partidos/{id}/resumen-jugadores`.
   El plan es por equipo y el resumen es del partido entero; embebrlo obligaría a
   recalcular por cada equipo. Se pide una vez por partido.
2. **Punto de entrada de la vista del árbitro:** se define con precisión al mapear
   la navegación en el plan de ejecución (RefLiveScreen vs. menú del partido).
3. **Fallback de avatar:** mismo diseño conceptual (inicial sobre fondo degradado)
   con **implementaciones nativas separadas** por plataforma (CSS en web, componente
   RN en móvil). No se comparte código entre plataformas.

## Fuera de alcance

- Limpiar la tabla `alineaciones` muerta y sus endpoints (trabajo aparte).
- Que el árbitro confirme el plan como acta oficial (sería una feature nueva).
- Recorte interactivo de la foto por el usuario.
- Mover `PerfilScreen` a una carpeta compartida (higiene menor; se puede colar en
  el plan si se toca el archivo, pero no es objetivo).

## Alcance del PR

Grande pero coherente. Orden sugerido de implementación (se detalla en el plan):
1. API: columna + migración + Pillow + endpoints de foto + tests.
2. API: helper de resumen de eventos + endpoint + tests.
3. Web: proxy de foto + reestructura del detalle del partido.
4. Móvil: fotos en LineupScreen.
5. Móvil: `LineupPitch` + vista del árbitro con pestañas.

Antes de montar las EC2 sigue pendiente sacar `apiUrl` a variable de entorno
([[apiurl-hardcodeada-mobile]]); no lo toca este trabajo, pero el móvil sumará
más llamadas autenticadas con imagen, que dependen de esa URL.
