# Checklist de validación en dispositivo — fotos de perfil y alineaciones

Todo lo del backend y la web ya está verificado (232 tests, render web probado
contra datos reales). Esto cubre **lo único que no se puede probar sin un teléfono**:
que la app móvil realmente renderice las fotos autenticadas, los distintivos, las
pestañas y el flujo de subir/quitar foto.

## Preparación

1. Backend arriba: `docker compose up -d` (ya lo está).
2. En `mobile/app.json`, `extra.apiUrl` apuntando a la **IP LAN de tu PC** (no
   localhost — el teléfono no lo resuelve). Ej: `http://192.168.x.x:8000`.
3. `cd mobile && npx expo start --tunnel`
4. Abre **Expo Go** en el teléfono y escanea el QR.

> Nota: `expo-image-picker` (nuevo en esta rama) ya viene incluido en Expo Go, así
> que no necesitas un build personalizado para probarlo.

## Credenciales de prueba (BD de desarrollo)

| Rol | Correo | Contraseña |
|-----|--------|-----------|
| Jugador | jugador@demo.com | demo1234 |
| Entrenador | entrenador@demo.com | demo1234 |
| Árbitro | arbitro@demo.com | demo1234 |
| Superadmin (web) | superadmin@demo.com | admin1234 |

Ya subí fotos de prueba a Juan Ramírez (juan@demo.com), Cristiano Ronaldo
(cr7@demo.com) y Diego Soto (diego@demo.com), todos con `demo1234`.

## 1. Subir / quitar foto (Task 10) — como JUGADOR

- [ ] Entra como **jugador@demo.com**. Ve a **Mi Perfil**.
- [ ] Arriba debe verse un avatar con tu **inicial** (aún sin foto).
- [ ] Pulsa **Cambiar foto** → concede permiso de galería → elige una imagen →
      recórtala cuadrada.
- [ ] Tras subir, el avatar del perfil debe cambiar a **tu foto** (sin reiniciar).
- [ ] Pulsa **Quitar foto** → confirma → el avatar vuelve a la **inicial**.
- [ ] Repite como **entrenador@demo.com** (pantalla Perfil, tema dorado) y como
      **arbitro@demo.com** (mismo componente Perfil). El botón debe funcionar igual.

**Qué estás validando:** el picker abre, la subida multipart con token llega al
API, y `refrescar()` actualiza la UI al instante.

## 2. Fotos en la alineación del ENTRENADOR (Task 8)

- [ ] Entra como **entrenador@demo.com** → **Mis Equipos** → un equipo con partido
      → arma/edita la **alineación**.
- [ ] En la cancha, cada jugador colocado debe mostrar su **foto** (si la tiene) o
      su **inicial**. Juan Ramírez y Cristiano Ronaldo deberían salir con foto.
- [ ] Debajo de cada uno, el **#dorsal y nombre**.
- [ ] Cambia de formación (4-4-2 / 4-3-3 / 3-5-2): los jugadores se recolocan y las
      fotos siguen con ellos.

**Qué estás validando:** el `<Avatar>` renderiza la imagen autenticada dentro de
la cancha, no solo iniciales.

## 3. Vista de alineaciones del ÁRBITRO (Task 9) — lo más nuevo

- [ ] Entra como **arbitro@demo.com** → **Partidos asignados** → abre un partido
      (RefLive, "Partido en vivo").
- [ ] Pulsa el botón nuevo **Ver alineaciones**.
- [ ] Debe abrir una pantalla con **dos pestañas**: el equipo local y el visitante.
- [ ] En la pestaña con alineación: la **cancha con las fotos** de los jugadores y
      los **distintivos** encima (balón con número si marcó, tarjeta, flechas de
      cambio) según los eventos del partido.
- [ ] Cambia a la otra pestaña: si ese equipo **no armó alineación**, debe verse
      **"Alineación no registrada"** centrado, sin romper la cancha.

**Qué estás validando:** las pestañas cambian de equipo, `LineupPitch` pinta fotos
+ distintivos desde `resumen-jugadores`, y el caso de equipo sin plan.

> Sugerencia: el **partido 1** de la BD tiene alineación del local (con las 3 fotos
> que subí) y eventos (un gol de Cristiano), y el visitante sin alineación — es el
> mejor caso para ver todo a la vez.

## 4. Coherencia con el panel web (opcional)

- [ ] La foto que subiste como jugador en el móvil debe verse también en el panel
      web: entra a **http://localhost:5000** como superadmin, abre el detalle de un
      partido donde ese jugador esté alineado — su foto aparece en la cancha.

**Qué estás validando:** una sola foto sirve para móvil y web (mismo endpoint).

---

## Si algo falla

Anota **qué rol, qué pantalla y qué viste** (o una captura) y me lo pasas. Lo más
probable que revisar si una foto no aparece:
1. ¿`apiUrl` apunta a la IP LAN correcta? (una foto que no carga suele ser esto).
2. ¿El backend está arriba? (`docker compose ps`).
3. Si la foto no aparece pero la inicial sí → el `<Image>` autenticado no cargó
   (problema de red/URL, no de lógica).
