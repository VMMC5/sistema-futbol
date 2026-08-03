# Filtros del panel + select de árbitro consistente

**Fecha:** 2026-08-03 · **Estado:** aprobado en conversación

## Objetivo

Seis mejoras chicas del panel web pedidas por el usuario tras estrenar
"Iniciar torneo": estilizar el select de asignar árbitro como los demás, y un
filtro por pestaña (Usuarios, Canchas, Partidos, Sedes, Reservas).

## Diseño

**Patrón único** (el del filtro de Solicitudes, PR #17): `<form method="get"
class="filter-bar">` + `<select data-autosubmit>` (auto-submit vía `panel.js`,
compatible con la CSP) + opción "Todos" por defecto; el valor elegido persiste
al recargar. La barra va entre el `section-head` y la tabla.

| Pestaña | Filtro | Mecanismo |
|---|---|---|
| Usuarios | Rol (4) + Activos/Inactivos, combinables | `rol` ya existe en la API; **se agrega `activo: bool \| None`** (con test) |
| Canchas | Sede (dropdown de sedes) | `sede_id` ya existe en la API |
| Partidos | Estado (programado/en curso/finalizado) | `estado` ya existe en la API |
| Sedes | Ciudad (ciudades distintas existentes) | filtrado en el panel (la API no filtra por ciudad; ~10 sedes) |
| Reservas | Estado (pendiente/confirmada/cancelada) | filtrado en el panel |

**Select de árbitro** (`partido_detalle.html`): el form de asignación adopta la
clase `filter-bar` (con `margin-bottom:0` porque vive dentro de una card) para
heredar el estilo de selects del panel. Cero CSS nuevo.

## Fuera de alcance

Filtros combinados entre pestañas, búsqueda de texto nueva, paginación, filtros
en la app móvil.

## Verificación

Tests de API para `activo` (solo, combinado con `rol`, y sin parámetro);
`ast.parse` de `app.py`; validación visual del usuario tras el despliegue.
