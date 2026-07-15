# Notificaciones push (IF-11) — demo en dispositivo real

El backend y el móvil quedan listos. Para probar el push físico (Expo Go SDK 53+
ya no soporta push remoto), se necesita un **development build** con EAS:

1. Crear un proyecto EAS: `cd mobile && npx eas init` (genera el `projectId`).
2. Pegar ese `projectId` en `mobile/app.json` → `expo.extra.eas.projectId`.
3. Build de desarrollo: `npx eas build --profile development --platform android`.
4. Instalar el build en un teléfono físico e iniciar sesión: al conceder permiso,
   el token se registra vía `POST /notificaciones/dispositivos`.
5. Disparar un evento (invitar al jugador a un equipo, o confirmar un pago suyo):
   el teléfono recibe el push. La notificación también queda en la pantalla de
   Avisos (respaldo por polling).

El envío se hace best-effort desde `api/app/notificaciones_service.py`; los tokens
que Expo reporte como `DeviceNotRegistered` se purgan solos.
