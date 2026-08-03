# Filtros del panel — Plan (ejecución inline)

> Ejecución inline aprobada por el usuario (feature chica). Spec:
> `docs/superpowers/specs/2026-08-03-filtros-panel-design.md`.

**Global:** rama `feat/filtros-panel`; tests `cd api && .venv/bin/pytest ...`;
español; sin `<script>` inline.

## Task 1: API — `activo` en `listar_usuarios` (TDD)

- Test nuevo en `api/tests/test_usuarios.py`: desactivar un usuario vía
  `PUT /usuarios/{id}` y comprobar `?activo=false` (lo incluye), `?activo=true`
  (lo excluye), `?rol=jugador&activo=true` (combina) y sin parámetro (todos).
- Implementación: parámetro `activo: bool | None = None` + filtro
  `models.Usuario.activo == activo` cuando no sea None.
- Commit: `feat(api): filtro activo en el listado de usuarios`

## Task 2: Panel — rutas y plantillas

- `web/app/app.py`: `usuarios()` lee `rol`/`activo` de `request.args` y los pasa
  a `api_get("/usuarios", ...)`; `canchas()` lee `sede_id` (+ carga `/sedes`
  para el dropdown); `partidos()` lee `estado`; `sedes()` filtra por `ciudad`
  en Python y arma la lista de ciudades distintas; `reservas()` filtra por
  `estado` en Python. Cada ruta pasa a la plantilla el valor elegido.
- Plantillas (`usuarios/canchas/partidos/sedes/reservas.html`): barra
  `filter-bar` con `data-autosubmit` tras el `section-head`, patrón de
  `solicitudes.html`.
- `partido_detalle.html`: el form de asignar árbitro adopta `class="filter-bar"`
  con `style="margin-bottom:0;"`.
- Verificación: `ast.parse` de `app.py`.
- Commit: `feat(web): filtros en usuarios, canchas, partidos, sedes y reservas`

## Task 3: Verificación final

- `cd api && .venv/bin/pytest tests/test_usuarios.py -q` + suite completa.
- Push + PR (aprobado por el usuario; él lo revisa y mergea).
