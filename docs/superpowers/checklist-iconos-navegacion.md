# Checklist de validación en dispositivo — iconos de navegación y pantallas

Lo estático ya está verificado: los archivos tocados parsean, los 16 iconos pasan
sus aserciones, todo `nombre=` usado existe en el catálogo, y los 233 tests de
Python siguen en verde.

**Lo que esto busca:** una errata en un nombre de icono no da error, da un hueco
invisible. La comprobación cruzada descarta nombres inexistentes, pero no que un
icono esté puesto en la pestaña equivocada. Por eso hay que mirar las cuatro barras.

## Preparación
1. Backend arriba: `docker compose up -d`.
2. `cd mobile && npx expo start` (modo LAN, **sin** `--tunnel`) y escanea el QR con
   Expo Go. En modo LAN la IP de la API se deriva sola; no toques `app.json`.
3. Si tras instalar iconos nuevos el bundle falla, arranca con `npx expo start -c`.

## 1. Barra de navegación — los cuatro roles
- [ ] **Sin sesión** (pública): dos pestañas, INICIO con una **casa** y TORNEOS con
      una **copa**. La activa en verde, la otra en gris.
- [ ] **Jugador** (jugador@demo.com / demo1234): INICIO casa, TORNEOS copa,
      RESERVAR CANCHA **calendario**, MI PERFIL **persona**.
- [ ] **Entrenador** (entrenador@demo.com / demo1234): INICIO casa, MIS EQUIPOS
      **gente**, TORNEOS copa, PERFIL persona.
- [ ] **Árbitro** (arbitro@demo.com / demo1234): PARTIDOS ASIGNADOS **balón**,
      HISTORIAL **reloj/historial**, PERFIL persona.
- [ ] Ninguna pestaña muestra un hueco vacío donde debería ir su icono.
- [ ] El puntito gris de antes ya no aparece en ninguna barra.
- [ ] La barra no se ve desproporcionadamente alta ni recorta las etiquetas.

## 2. Pantallas
- [ ] **TORNEOS** (cualquier rol): cada torneo de la lista lleva una **copa** dentro
      del círculo verde, no un emoji.
- [ ] **INICIO del jugador**: "Ver mis estadísticas" con un **gráfico** blanco, y
      "Próximos partidos" con un **calendario** verde. Icono y texto en la misma
      línea, centrados, sin que el texto se parta.
- [ ] **RESERVAR CANCHA**: el buscador muestra un **marcador de mapa** a la
      izquierda y el texto gris "Buscar sede". Al escribir, el texto no se monta
      sobre el icono y el filtrado de sedes sigue funcionando.
- [ ] **INICIO del entrenador**: la rejilla muestra gente / documento con "+" /
      portapapeles con lista / calendario, en ese orden. "Inscribir" y "Reservar"
      siguen avisando "Disponible próximamente".

## Si algo falla
Anota **rol, pantalla y qué viste** (o captura). Lo más probable:
1. Hueco vacío donde va un icono → nombre mal escrito; comprueba la clave contra
   `mobile/src/components/iconos-datos.json`.
2. Icono correcto pero en la pestaña equivocada → revisa `tabBarIcon` en `App.js`.
3. Icono incompleto o deformado → falta un path; vuelve a generar con
   `node scripts/generar-iconos.cjs`.
4. "Unable to resolve module" → caché de Metro; `npx expo start -c`.
