# App móvil (React Native + Expo)

App para jugadores, entrenadores y árbitros. Al abrir muestra un **panel público**
con la información más relevante (próximos partidos, torneos activos, goleadores)
sin necesidad de iniciar sesión.

## Pantallas

- **Inicio (pública)**: resumen del sistema. Botón "Ingresar" arriba a la derecha.
- **Login**: inicia sesión; si es el primer ingreso con contraseña temporal, manda
  a la pantalla de cambio obligatorio.
- **Crear cuenta (jugador)**: auto-registro estándar.
- **Entrenador / Árbitro**: envía una **solicitud** con un documento (PDF o imagen)
  que el administrador revisa. Si la acepta, llega un correo con una contraseña
  temporal.
- **Cambiar contraseña**: obligatoria en el primer ingreso de cuentas creadas por
  el administrador.
- **Mi panel**: contenido según el rol del usuario.

## Requisitos

- Node LTS y la app **Expo Go** en el teléfono.
- La API corriendo (`docker compose up` en la raíz del proyecto) con datos
  (`alembic upgrade head` + `python -m app.seed`).

## Configurar la URL de la API (IMPORTANTE)

En modo LAN normal no hay que configurar nada: la app reutiliza la IP del
servidor de Expo. Si usas **modo túnel** (`npx expo start --tunnel`, p. ej. con
WSL2), copia la plantilla y pon la **IP local de la máquina** que corre la API:

```bash
cp .env.example .env     # y edita EXPO_PUBLIC_API_URL
```

Desde un teléfono físico `localhost` NO apunta a tu PC; para conocer tu IP:
`ipconfig` (Windows) o `ifconfig`/`ip a` (Mac/Linux). El teléfono y la PC deben
estar en la misma red Wi-Fi. El `.env` está ignorado por git — la URL de la API
ya no se versiona; en builds de producción se define en la configuración de EAS
(env o secret), no en el repo.

## Arranque

```bash
cd mobile
npm install          # o: npx expo install   (alinea versiones de Expo)
npx expo start
```

Escanea el QR con **Expo Go**.

## Notas

- El token JWT se guarda con `expo-secure-store` y se envía como `Bearer` en cada
  llamada protegida.
- El documento de la solicitud se sube con `expo-document-picker` mediante
  `multipart/form-data`.
- El correo de aprobación, en desarrollo (sin SMTP configurado en la API), se
  **imprime en la consola del contenedor de la API**. Para envío real, define las
  variables `SMTP_*` en el `.env`.
