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
> demo1234**, abre un partido asignado, inícialo y registra, en este orden:
> 1. Gol del **jugador X** (sin asistencia).
> 2. Otro gol del **jugador X** (sin asistencia): queda con dos goles.
> 3. Gol de **otro jugador** del mismo equipo, marcando al **jugador X** en la
>    lista "Asistencia (opcional)" que aparece debajo del anotador al registrar
>    un gol: así X suma también una asistencia.
> 4. Tarjeta amarilla al **jugador X**: queda con tres distintivos acumulados
>    (dos goles, una asistencia, una amarilla).
> 5. Tarjeta roja al **mismo jugador X**: la pantalla no lo excluye de la lista
>    por tener ya una amarilla, así que queda con **cuatro** distintivos
>    acumulados.
> 6. Un cambio (cualquier titular por uno de la banca).

## 1. Botones de evento (2x2) — ÁRBITRO
- [ ] En el partido en vivo, antes de registrar nada, mira los cuatro botones:
      **Gol**, **Amarilla**, **Roja**, **Cambio**. Cada uno muestra un icono
      vectorial a color, no un emoji.
- [ ] Gol lleva el **balón**; Amarilla y Roja llevan el mismo icono de
      **rectángulo de tarjeta** (solo cambia el color); Cambio lleva las
      **flechas de intercambio**.
- [ ] El icono se distingue del fondo de su propio botón: en **Amarilla**
      (fondo amarillo) el icono va en un tono oscuro de contraste, no en el
      color de la tarjeta; en **Roja** (fondo rojo) el icono va en blanco.

## 2. Lista de eventos en vivo — ÁRBITRO
- [ ] Cada evento de la lista muestra su icono a la izquierda: **balón** en goles,
      **rectángulo amarillo** o **rojo** en tarjetas, **flechas de intercambio** en
      cambios.
- [ ] El texto sigue completo: minuto, nombre del jugador, y en el cambio "X por Y".
- [ ] Ningún renglón muestra `[object Object]`. Si aparece, un consumidor quedó
      con el tipo viejo.

## 3. Alineaciones (distintivos) — ÁRBITRO
- [ ] Abre **Ver alineaciones** desde el partido en vivo.
- [ ] El **jugador X** acumula **cuatro** distintivos (dos goles, una
      asistencia, una amarilla y una roja) sin salirse de la foto ni
      solaparse de forma ilegible.
- [ ] El balón del jugador X muestra **×2**, no dos balones ni "⚽×2".
- [ ] La asistencia del jugador X muestra la **"A"** (sin ×N, porque es una sola).
- [ ] El jugador X muestra **los dos rectángulos de tarjeta, adyacentes**: el
      amarillo y el rojo se distinguen bien entre sí y no se confunden pese a
      ser el mismo icono en dos colores.
- [ ] Las flechas **↑ ↓** de entra/sale siguen siendo flechas: no se tocaron.
- [ ] **Contraste:** todos los distintivos se leen sobre el verde de la cancha. El
      balón y la "A" van en blanco con sombra, la amarilla en amarillo y la roja en
      un rojo claro, a propósito. Si alguno se pierde contra el fondo, dilo: los
      emoji de antes traían su propio color y estos no.
- [ ] **Banca:** baja a la lista de **Banca** y revisa a un suplente que haya
      entrado en un cambio (`entro: true`). Su distintivo **↑** debe leerse
      oscuro sobre el fondo claro de la banca, no blanco (blanco sobre casi
      blanco desaparece). Comprueba también que los distintivos no se salgan
      de la tarjeta del jugador ni se solapen con la fila de abajo.

## 4. Resumen del partido — ÁRBITRO
- [ ] Firma el acta y abre el resumen. Las secciones **Goles** y **Tarjetas**
      muestran icono a la izquierda y el texto a la derecha, sin partirse.
- [ ] El `✓` de acta firmada sigue siendo un `✓`: está fuera de alcance.

## 5. Notificaciones — JUGADOR
- [ ] Entra como **jugador@demo.com / demo1234** → campana de INICIO.
- [ ] Los avisos de gol muestran un **balón**, los de torneo una **copa**, y el
      resto una **campana**, dentro de su círculo de color.
- [ ] Los avisos de **pago** siguen mostrando `$` y los de **convocatoria** `!`.
      Es lo esperado: no son emoji y quedan fuera de alcance.
- [ ] La `✕` de descartar sigue siendo una `✕`.

## 6. Los dos sueltos
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
