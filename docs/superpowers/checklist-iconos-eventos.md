# Checklist de validación en dispositivo — iconos de eventos y restantes

Lo estático está verificado: los archivos parsean, los 20 iconos pasan sus
aserciones, todos los nombres de icono existen, y los 233 tests de Python siguen
en verde.

**Lo que esto busca:** dos funciones cambiaron su tipo de retorno
(`resumenEvento` y `badgesDe`). Es el primer trabajo de las tres tandas de iconos
que puede romper comportamiento, no solo aspecto.

## Preparación

1. Backend arriba: `docker compose up -d`. Si es una BD nueva, siembra los datos
   demo: `docker compose exec api python -m app.seed`.
2. `cd mobile && npx expo start` (modo LAN, **sin** `--tunnel`) y escanea el QR.
3. Si el bundle sale raro tras el cambio de iconos: `npx expo start -c`.

> **Necesitas un partido con eventos.** Sin goles, tarjetas ni cambios no se
> puede validar nada de lo estructural. Entra como **arbitro@demo.com /
> demo1234**, abre un partido asignado, inícialo y registra: dos goles del mismo
> jugador, una tarjeta amarilla, una roja a otro jugador, y un cambio.

## 1. Lista de eventos en vivo — ÁRBITRO
- [ ] Cada evento de la lista muestra su icono a la izquierda: **balón** en goles,
      **rectángulo amarillo** o **rojo** en tarjetas, **flechas de intercambio** en
      cambios.
- [ ] El texto sigue completo: minuto, nombre del jugador, y en el cambio "X por Y".
- [ ] Ningún renglón muestra `[object Object]`. Si aparece, un consumidor quedó
      con el tipo viejo.

## 2. Alineaciones (distintivos) — ÁRBITRO
- [ ] Abre **Ver alineaciones** desde el partido en vivo.
- [ ] El goleador con dos goles muestra **balón ×2**, no "⚽×2" ni solo el balón.
- [ ] El amonestado muestra el **rectángulo amarillo**; el expulsado, el **rojo**.
- [ ] Si hay asistencia, aparece una **"A"** (con ×N si hay más de una).
- [ ] Las flechas **↑ ↓** de entra/sale siguen siendo flechas: no se tocaron.
- [ ] Con cuatro distintivos sobre un mismo jugador, no se salen de la foto ni se
      solapan de forma ilegible.
- [ ] **Contraste:** todos los distintivos se leen sobre el verde de la cancha. El
      balón y la "A" van en blanco con sombra, la amarilla en amarillo y la roja en
      un rojo claro, a propósito. Si alguno se pierde contra el fondo, dilo: los
      emoji de antes traían su propio color y estos no.

## 3. Resumen del partido — ÁRBITRO
- [ ] Firma el acta y abre el resumen. Las secciones **Goles** y **Tarjetas**
      muestran icono a la izquierda y el texto a la derecha, sin partirse.
- [ ] El `✓` de acta firmada sigue siendo un `✓`: está fuera de alcance.

## 4. Notificaciones — JUGADOR
- [ ] Entra como **jugador@demo.com / demo1234** → campana de INICIO.
- [ ] Los avisos de gol muestran un **balón**, los de torneo una **copa**, y el
      resto una **campana**, dentro de su círculo de color.
- [ ] Los avisos de **pago** siguen mostrando `$` y los de **convocatoria** `!`.
      Es lo esperado: no son emoji y quedan fuera de alcance.
- [ ] La `✕` de descartar sigue siendo una `✕`.

## 5. Los dos sueltos
- [ ] **Mi panel** (jugador): el botón "Mis invitaciones a equipos" lleva un
      **sobre** delante, sobre el fondo lima.
- [ ] **Crear cuenta → Entrenador/Árbitro**: pulsa "Adjuntar documento" y elige un
      archivo. Al seleccionarlo aparece un **clip** y el nombre del archivo. Antes
      de elegir, el botón dice solo "Adjuntar documento", sin icono.

## Si algo falla
Anota **rol, pantalla y qué viste** (o captura). Lo más probable:
1. `[object Object]` en la lista de eventos → un consumidor de `resumenEvento`
   quedó con el tipo viejo.
2. Distintivo sin icono pero con el ×N → el nombre de icono no existe; revisa
   `mobile/src/components/iconos-datos.json`.
3. Tarjeta del color equivocado → revisa el ternario de `t.tipo === "tarjeta_roja"`.
4. Hueco vacío donde va un icono → nombre mal escrito.
5. "Unable to resolve module" → caché de Metro; `npx expo start -c`.
