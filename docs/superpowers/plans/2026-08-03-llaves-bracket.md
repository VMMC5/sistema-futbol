# Llaves (bracket) — Plan (ejecución inline)

> Spec: `docs/superpowers/specs/2026-08-03-llaves-bracket-design.md`. Rama
> `feat/llaves-bracket`. Ejecución inline aprobada.

**Global:** español; sin `<script>` inline; tests del builder con el pytest del
venv de la API (`cd web && ../api/.venv/bin/pytest tests/ -q`).

## Task 1: builder `construir_llaves` (TDD)

- `web/tests/test_llaves.py` con 5 casos: 8 equipos completo (2 columnas por
  lado, final y campeón), 6 equipos (hojas bye en la columna de ronda 1),
  parcial (solo ronda 1 de 8 → `final=None`, mitades 2/2), 2 equipos (solo
  centro), sin partidos (`None`).
- `web/app/llaves.py`: reconstrucción hacia atrás + orden por adyacencia +
  nombres de ronda.
- Commit: `feat(web): builder del bracket de eliminacion (construir_llaves)`

## Task 2: ruta + plantilla + CSS

- `web/app/app.py`: ruta `torneo_llaves(torneo_id)`; redirige a `tabla` si el
  torneo no es eliminación.
- `web/app/templates/llaves.html` + estilos `.bracket*` en `styles.css`
  (columnas flex, tarjetas, conectores por pareja con variante espejada,
  centro con campeón).
- `torneos.html`: botón "Llaves" para eliminación (reemplaza "Tabla").
- Verificación: `ast.parse` de `app.py`.
- Commit: `feat(web): vista de llaves con la final al centro`

## Task 3: verificación + PR

- Tests del builder + suite completa de la API (no debería tocarla, corre como
  red de seguridad) + push + PR para revisión del usuario.
