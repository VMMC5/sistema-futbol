# Reglas del partido en vivo: expulsión por doble amarilla y quién puede recibir eventos

Fecha: 2026-07-29
Estado: aprobado por el usuario, pendiente de plan de implementación

## Problema

Al validar la app del árbitro en un partido real salieron tres defectos de regla de
negocio, todos de la misma familia: **el sistema no sabe quién está realmente en el
campo**.

1. **La segunda amarilla no expulsa.** El árbitro puede registrar dos amarillas al
   mismo jugador y no pasa nada: hay que acordarse de poner la roja a mano.
2. **Un jugador expulsado sigue pudiendo recibir eventos.** Goles, asistencias, más
   tarjetas: nada lo impide, ni en la app ni en el API.
3. **El que entra en un cambio no aparece en las listas del árbitro**, así que no se
   le puede registrar nada. Y su reverso: **el que sale sigue apareciendo**.

La causa común está en dos sitios. En el móvil, `RefEventScreen.js:90` calcula el
pool de jugadores como `datosEquipo.titulares` — la alineación que registró el
entrenador **antes** del partido, congelada. En el API, `registrar_evento`
(`api/app/routers/partidos.py:252`) solo comprueba que el partido esté en juego y que
el equipo participe; no mira al jugador.

## Alcance

**Dentro:**

- La regla de "quién está en el campo", calculada en el servidor.
- Expulsión automática al registrar la segunda amarilla.
- Rechazo en el API de eventos sobre jugadores que no están en el campo.
- Filtrado de las listas de `RefEventScreen` para que el árbitro no vea a quien no
  puede elegir.

**Fuera:**

- **Notificaciones para entrenador y árbitro.** Es la otra mitad de lo que pidió el
  usuario y va en su propio spec: no comparte archivos ni concepto con esto, y su
  parte cara está en generar los avisos en el backend, no en la pantalla.
- **Corrección de datos históricos.** Si en partidos ya jugados hay alguien con dos
  amarillas y sin roja, se queda así. La regla aplica de aquí en adelante.
- **Límite de jugadores por equipo.** En el fútbol real un expulsado no se
  reemplaza y el equipo juega con diez. Este sistema no lleva la cuenta de cuántos
  hay en el campo y añadirlo no es lo que se pidió.

## Decisiones tomadas

| Decisión | Elegido | Por qué |
|---|---|---|
| Alcance de "en el campo" | Titulares − expulsados − salidos + entrados | Elección del usuario. El que sale es el mismo defecto que el que entra, y excluirlo no cuesta código extra: es el mismo cálculo. |
| Dónde vive la regla | **Servidor**, expuesta al cliente | Una regla que solo vive en la app no es una validación: se salta llamando al API. Una que solo vive en el servidor da mala experiencia: el árbitro elige y recibe un error en mitad del partido. Van las dos, con **una sola implementación**. |
| Cómo llega al cliente | Campo `en_campo` en la salida del plan | `RefEventScreen` ya pide `/partidos/{id}/plan?equipo_id=` para cada equipo. Añadirlo ahí le da el dato **sin una llamada extra** y sin recalcular nada. |
| Forma de la expulsión automática | Un evento `tarjeta_roja` adicional | Los distintivos, el acta y las estadísticas ya cuentan `rojas` leyendo eventos: no hay que tocar ninguno. La alternativa (marcar la amarilla) obligaría a cambiar los cuatro consumidores. |
| Datos históricos | No se tocan | Corregirlos es una decisión aparte, no un efecto colateral de esta. |

## Arquitectura

### La regla

```
en_campo(equipo) = titulares del plan
                 − expulsados      (rojas > 0, sea directa o por doble amarilla)
                 − salidos         (salio == True)
                 + entrados        (entro == True)
```

`api/app/eventos_resumen.py::resumen_por_jugador` **ya devuelve** por jugador
`{goles, asistencias, amarillas, rojas, salio, entro}`. La regla es una función de
lectura sobre eso más el plan: **no hace falta ninguna tabla, columna ni migración**.

**Caso sin alineación registrada — y no es opcional.** Hoy `RefEventScreen.js:90` cae
a la plantilla completa cuando el equipo no tiene plan
(`titulares.length ? titulares : suplentes`), para que el árbitro pueda arbitrar
igualmente. Ese comportamiento **se conserva**: si no hay titulares, la plantilla
entera cuenta como "en el campo", menos los expulsados.

No es una comodidad: **es lo que sostiene los tests de eventos que ya existen**. El
helper `_partido_en_juego` de `api/tests/test_arbitro_eventos.py:5-9` crea el partido
**sin registrar ninguna alineación**, y todos los tests de goles, tarjetas y
correcciones de ese archivo registran eventos sobre él. Sin el fallback, la regla
nueva los rechazaría todos y la suite se caería. Quien implemente esto no debe
"simplificarlo" quitándolo.

### Servidor: `PlanItemOut` gana `en_campo`

`PlanItemOut` (`api/app/schemas.py:459`) añade `en_campo: bool = False`, y
`_plan_a_salida` (`api/app/routers/partidos.py:443`) lo rellena para titulares y
suplentes usando la regla. Es el mismo endpoint que ya consume la app, así que no
cambia el número de llamadas.

### Servidor: `registrar_evento` valida

`registrar_evento` rechaza con **409** lo que contradiga la regla. Las condiciones
dependen del tipo de evento, y el cambio es el que rompe la simetría porque el que
entra está en la banca justamente por no estar en el campo:

| Evento | `jugador_id` | `jugador_secundario_id` |
|---|---|---|
| `gol` | en el campo, **si viene** | asistente: en el campo, si viene |
| `tarjeta_amarilla` / `tarjeta_roja` | en el campo | — |
| `cambio` | el que sale: en el campo | el que entra: **no** en el campo y **no** expulsado |

**Un evento puede no llevar jugador, y eso es legal.** `test_arbitro_eventos.py:43`
registra un autogol atribuido solo al equipo, sin `jugador_id`:
`{"tipo": "gol", "equipo_id": 1, "subtipo": "autogol", "minuto": 30}`. La validación
debe **saltarse la comprobación cuando el campo viene vacío**, no rechazar. Lo mismo
con el asistente, que es opcional. Solo el `cambio` exige ambos.

Un `cambio` exige ambos jugadores: sin saber quién sale y quién entra la regla no se
puede aplicar. Hoy eso solo se valida en el cliente
(`RefEventScreen.js`), así que la comprobación pasa también al servidor.

### Servidor: la segunda amarilla expulsa

Al registrar una `tarjeta_amarilla`, si el jugador **ya tenía una** en ese partido,
`registrar_evento` crea **además** un evento `tarjeta_roja` en la misma transacción:
mismo partido, equipo, jugador y minuto, con `detalle` indicando que viene de doble
amarilla, para distinguirla de una roja directa en el acta.

El endpoint sigue devolviendo la amarilla, que es lo que se pidió crear.
`RefLiveScreen` recarga con `useFocusEffect` al volver de la pantalla de evento
(`RefLiveScreen.js:65`), así que el árbitro ve aparecer la roja sin hacer nada.

Intentar registrar una roja a alguien ya expulsado queda rechazado por la regla
general del apartado anterior; no necesita un caso propio.

### Cliente: `RefEventScreen` filtra

`RefEventScreen.js:90` pasa de `datosEquipo.titulares` a los jugadores con
`en_campo` verdadero, uniendo titulares y suplentes en un solo pool. Para el evento
de tipo `cambio`, la lista de "quién entra" es la complementaria: los que **no**
están en el campo y no están expulsados.

El cliente **no recalcula la regla**: solo lee el campo que el servidor le da. Si
mañana la regla cambia, cambia en un sitio.

## Flujo de datos

Ninguna llamada nueva. `RefEventScreen` ya pedía el plan de cada equipo; ahora ese
plan viene con `en_campo` por jugador. `registrar_evento` calcula la regla en
servidor a partir del plan y los eventos ya guardados.

## Manejo de errores

Los rechazos son **409**, coherentes con el resto del router
(`partidos.py` ya usa 409 para "solo se pueden registrar eventos mientras el partido
está en juego" y para la alineación fuera de plazo). Cada mensaje dice **por qué** el
jugador no es elegible —expulsado, ya salió, no está en el campo— para que el árbitro
entienda el rechazo si llega a verlo.

Con el filtrado del cliente, ese 409 no debería aparecer en uso normal: es la red por
si la app va desactualizada o alguien llama al API directamente.

## Verificación

A diferencia de las tres tandas de iconos, **aquí sí hay tests reales**: es backend, y
la suite de Python cubre `api/`. Casos previstos:

- Segunda amarilla genera la roja automática, con su `detalle`.
- Una sola amarilla **no** genera roja.
- Evento sobre un jugador expulsado: 409.
- Evento sobre un jugador que ya salió: 409.
- Evento sobre un jugador que entró de cambio: **aceptado**.
- `cambio` con el que sale fuera del campo: 409.
- `cambio` con el que entra ya en el campo: 409.
- `cambio` sin uno de los dos jugadores: 409.
- Equipo sin alineación registrada: la plantilla entera es elegible.
- `en_campo` en la salida del plan refleja la regla tras cada tipo de evento.

La suite pasa de **233** a unos **243**. Todo lo demás debe seguir en verde: la
regla nueva no debe romper los tests de partidos, alineaciones ni estadísticas que ya
existen.

La app se verifica con `npm run verificar` y validación en dispositivo sobre un
partido con doble amarilla y un cambio.

## Riesgos

- **Es la primera vez en varias tandas que se tocan reglas de negocio del backend**,
  no presentación. Un rechazo mal calibrado deja al árbitro sin poder registrar un
  evento legítimo en mitad de un partido, que es peor que el defecto que arregla.
  Por eso los tests cubren tanto los rechazos como las aceptaciones.
- **El caso sin alineación registrada es el más fácil de romper.** Si la regla se
  aplica sin contemplarlo, un partido sin planes deja al árbitro con las listas
  vacías. Tiene test propio.
- **Partidos en curso durante el despliegue.** Un partido a medio arbitrar cuando
  entre el cambio pasará a evaluarse con la regla nueva sobre eventos ya
  registrados. No corrompe nada —la regla solo lee—, pero un jugador con dos
  amarillas previas y sin roja quedará marcado como expulsado y dejará de ser
  elegible. Es el comportamiento correcto, conviene saberlo.
