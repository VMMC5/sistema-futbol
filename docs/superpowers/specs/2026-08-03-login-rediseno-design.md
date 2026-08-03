# Rediseño del login del panel

**Fecha:** 2026-08-03 · **Estado:** aprobado (mockup del usuario adaptado)

## Objetivo

Implementar el mockup de login entregado por el usuario: fondo de franjas con
glow animado, marquesina de marcadores ficticios, tarjeta con logo flotante,
inputs con foco lima, botón ENTRAR con barrido y toggle VER/OCULTAR.

## Adaptaciones acordadas

1. Estilos inline y `style-hover/focus/onClick` del mockup → clases `.lg-*` y
   `@keyframes` en `styles.css` (la CSP bloquea handlers inline).
2. Tipografías del mockup (Archivo Expanded, Barlow, JetBrains Mono) SOLO en el
   login (página independiente); el panel interno conserva Bebas/Manrope.
3. Toggle de contraseña vía `panel.js` con `data-toggle-password` (patrón
   CSP-safe existente).
4. Marquesina decorativa con contenido ficticio (codificación corregida).
5. Mejoras sobre el mockup: flashes de error estilizados dentro de la tarjeta,
   credenciales demo visibles SOLO con `FLASK_ENV=development` (flag
   `mostrar_hint` desde la ruta), y logo.png real en el cuadro lima flotante.

## Plan (inline)

- `styles.css`: bloque `.lg-*` + keyframes `swp/flt/pls/mrq`.
- `login.html`: reescritura completa sobre la estructura del mockup.
- `panel.js`: manejador `data-toggle-password`.
- `app.py`: `mostrar_hint` en los `render_template("login.html")`.
- Verificación: ast.parse + visual del usuario (toggle, foco, error de login,
  hint ausente en producción).
