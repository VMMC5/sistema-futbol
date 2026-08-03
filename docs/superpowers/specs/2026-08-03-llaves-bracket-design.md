# Vista de llaves (bracket) para torneos de eliminación — panel web

**Fecha:** 2026-08-03 · **Estado:** aprobado en conversación (opción B: doble
lado con la final al centro; solo web)

## Objetivo

Botón **"Llaves"** en los torneos de eliminación del panel que abre un bracket
estilo mundial: rondas convergiendo desde ambos lados hacia la final al centro,
con marcadores, ganadores en negritas y el campeón destacado.

## Diseño

### Builder puro (`web/app/llaves.py`)

`construir_llaves(partidos: list[dict]) -> dict | None` — recibe los partidos
del torneo (JSON de `GET /partidos?torneo_id=`) y reconstruye el árbol **hacia
atrás desde la ronda más alta**, porque el sistema re-sortea cada ronda: el
alimentador de un participante es el partido de la ronda anterior donde jugó.
Sin alimentador → hoja **"Pase directo"** (bye; por invariante del sistema los
byes solo existen de la ronda 1 a la 2; si datos manuales lo violan, la hoja
se pinta igual donde caiga, sin relleno más profundo).

Estructura devuelta (pensada para Jinja sin recursión):

- `lados.izquierda` / `lados.derecha`: lista de columnas (ronda 1 → k-1), cada
  una `{titulo, slots}`; slots = partido | bye | vacío. El orden dentro de cada
  columna deja adyacentes a los dos alimentadores de cada partido de la
  columna siguiente (las líneas conectan de verdad).
- `final`: slot del partido de la ronda más alta cuando esa ronda tiene 1
  partido (aunque no esté jugado); si tiene varios (torneo a medias), `None` y
  el centro muestra "Final por definir", repartiendo los subárboles mitad y
  mitad.
- `campeon`: nombre si la final está `finalizado`.
- Nombres de ronda por nº de partidos: 1=Final, 2=Semifinales, 4=Cuartos de
  final, 8=Octavos de final, si no "Ronda de {2n}".
- Sin partidos con `jornada` → `None` (la vista avisa "sin calendario").

### Ruta y plantilla

- `GET /torneos/<id>/llaves` (login): valida con `_tipo_normalizado` que el
  torneo sea eliminación (si no, redirige a la tabla), pide los partidos y
  rinde `llaves.html`.
- `llaves.html`: columnas en flex con `overflow-x: auto`; tarjetas con fecha,
  equipos y marcador (ganador en negritas); conectores con bordes CSS sobre
  envoltorios de pareja (variante espejada para el lado derecho); caja central
  con la final y el campeón. **Cero JavaScript** (CSP intacta).
- `torneos.html`: torneos de eliminación muestran **"Llaves"** en lugar de
  "Tabla" (la tabla de posiciones no aplica a eliminación).

## Fuera de alcance

App móvil (posible segundo PR), tercer puesto (no existe en el sistema),
edición desde el bracket, llaves fijas (el re-sorteo es decisión del spec de
iniciar-torneo).

## Verificación

`web/tests/test_llaves.py` (pytest del venv de la API; `web/app` ya es
paquete): 8 equipos completo, 6 equipos con byes, torneo a media ronda 1,
torneo de 2 equipos, sin partidos. El CSS lo valida el usuario en el navegador
y se itera (sin headless).
