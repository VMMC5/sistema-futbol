// Notificaciones push (Expo). El backend envía vía Expo Push Service; aquí
// pedimos permiso, registramos el token del dispositivo y manejamos la llegada.
import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { apiPost, apiDelete } from "./api";

// Mostrar la notificación aunque la app esté en primer plano.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let _tokenActual = null;

// Pide permiso, obtiene el Expo push token y lo registra en la API.
export async function registrarParaPush() {
  if (!Device.isDevice) return; // los push remotos no funcionan en emulador
  try {
    const { status: previo } = await Notifications.getPermissionsAsync();
    let status = previo;
    if (status !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return;

    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    if (!projectId) return; // sin projectId de EAS no se puede obtener token

    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
    _tokenActual = token;
    await apiPost("/notificaciones/dispositivos", { token, plataforma: Platform.OS });
  } catch (_) {
    // best-effort: si falla el registro, la app sigue funcionando
  }
}

// Da de baja el token al cerrar sesión.
export async function desregistrar() {
  if (!_tokenActual) return;
  try {
    await apiDelete(`/notificaciones/dispositivos?token=${encodeURIComponent(_tokenActual)}`);
  } catch (_) {
    // ignorar
  } finally {
    _tokenActual = null;
  }
}

// Al tocar una notificación, abre la pantalla de Notificaciones. Devuelve limpieza.
export function configurarManejadores(navigationRef) {
  const sub = Notifications.addNotificationResponseReceivedListener(() => {
    if (navigationRef?.isReady?.()) {
      navigationRef.navigate("Notifications");
    }
  });
  return () => sub.remove();
}
