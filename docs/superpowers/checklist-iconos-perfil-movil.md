# Checklist de validación en dispositivo — iconos y menú de perfil

Lo estático ya está verificado: los 8 archivos tocados parsean
(`mobile/scripts/verificar-sintaxis.cjs`, sobre el `@babel/core` del proyecto),
los 5 iconos pasan sus aserciones, y los 233 tests de Python siguen en verde.
Esto cubre lo único que no se puede probar sin un teléfono: que los SVG
rendericen y que los tres roles vean su menú.

## Preparación
1. Backend arriba: `docker compose up -d`.
2. `mobile/app.json` → `extra.apiUrl` apuntando a la IP LAN de tu PC.
3. `cd mobile && npx expo start --tunnel` y escanea el QR con Expo Go.

> `react-native-svg` viene incluido en Expo Go: no hace falta build personalizado.

## 1. Jugador — jugador@demo.com / demo1234
- [ ] **INICIO**: la campana de la cabecera es un icono de línea blanco, no un emoji.
- [ ] Con notificaciones sin leer, el punto rojo sigue apareciendo sobre la campana.
- [ ] Pulsar la campana sigue abriendo NOTIFICACIONES.
- [ ] **MI PERFIL**: las 4 filas muestran iconos (lápiz, tarjeta, candado, salida),
      no emojis. El de "Cerrar sesión" es rojo, como su texto.
- [ ] "Editar datos personales" abre el modal con tu nombre y teléfono ya puestos;
      guardar actualiza el nombre de la cabecera.
- [ ] "Cambiar contraseña" navega. "Métodos de pago" avisa "Disponible próximamente".
- [ ] Cambiar y quitar foto siguen funcionando (no debe haber regresión del PR #20).

## 2. Entrenador — entrenador@demo.com / demo1234
- [ ] **PERFIL** ya no es la lista de botones vieja: avatar, nombre, insignia
      **ENTRENADOR** en dorado, correo debajo, y las 4 filas con iconos.
- [ ] "Editar datos personales" (nuevo para este rol) abre el modal, guarda y el
      nombre cambia. El botón "Guardar" es dorado.
- [ ] Cambiar y quitar foto funcionan; el avatar se actualiza sin reiniciar.
- [ ] "Cerrar sesión" vuelve al área pública.

## 3. Árbitro — arbitro@demo.com / demo1234
- [ ] **PERFIL** idéntico al del entrenador pero con la insignia **ARBITRO** en
      guinda y el botón "Guardar" guinda.
- [ ] "Editar datos personales" guarda correctamente.
- [ ] Cambiar y quitar foto funcionan.

## Si algo falla
Anota **rol, pantalla y qué viste** (o captura). Lo más probable:
1. Icono en blanco → nombre mal escrito en `OpcionMenu` (`edit`, `creditcard`,
   `lock`, `logout`, `bell`).
2. Icono negro sólido donde debería ser de línea → falta `trazo: true` en
   `iconos-datos.json`.
3. Pantalla en blanco al abrir Perfil → import roto tras mover `PerfilScreen`.
