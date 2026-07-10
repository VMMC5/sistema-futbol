// Cliente de la API + manejo del token.
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

const API_PORT = 8000;
const TIMEOUT_MS = 15000;

// En desarrollo, Expo sirve el bundle desde la IP de la máquina que corre el
// servidor, así que la reutilizamos para la API y no hay que editar app.json
// cada vez que cambia la red. En una build de producción no hay hostUri.
// En modo túnel hostUri es un dominio (exp.direct) que no expone la API: solo
// se acepta una IPv4, y si no, se cae al valor de app.json.
function _urlDesdeExpo() {
  const host = Constants.expoConfig?.hostUri?.split(":")[0];
  const esIPv4 = host && /^\d{1,3}(\.\d{1,3}){3}$/.test(host);
  return esIPv4 ? `http://${host}:${API_PORT}` : null;
}

export const API_URL =
  _urlDesdeExpo() || Constants.expoConfig?.extra?.apiUrl || `http://localhost:${API_PORT}`;

const TOKEN_KEY = "token";

export async function guardarToken(token) {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}
export async function leerToken() {
  return SecureStore.getItemAsync(TOKEN_KEY);
}
export async function borrarToken() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

async function _headers(conAuth) {
  const h = { "Content-Type": "application/json" };
  if (conAuth) {
    const t = await leerToken();
    if (t) h["Authorization"] = `Bearer ${t}`;
  }
  return h;
}

// Sin un timeout, una IP inalcanzable deja la promesa colgada para siempre y la
// pantalla se queda cargando sin mostrar error.
async function _fetch(path, opciones = {}) {
  const ctrl = new AbortController();
  const temporizador = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await fetch(`${API_URL}${path}`, { ...opciones, signal: ctrl.signal });
  } catch (e) {
    throw new Error(
      e.name === "AbortError"
        ? `El servidor (${API_URL}) no respondió a tiempo. Revisa que estés en la misma red Wi-Fi.`
        : `No se pudo conectar con el servidor (${API_URL}).`
    );
  } finally {
    clearTimeout(temporizador);
  }
}

async function _manejar(res) {
  let cuerpo = null;
  try {
    cuerpo = await res.json();
  } catch (_) {
    cuerpo = null;
  }
  if (!res.ok) {
    const detalle = (cuerpo && cuerpo.detail) || "Ocurrió un error";
    throw new Error(typeof detalle === "string" ? detalle : "Error de validación");
  }
  return cuerpo;
}

export async function apiGet(path, conAuth = true) {
  const res = await _fetch(path, { headers: await _headers(conAuth) });
  return _manejar(res);
}

export async function apiPost(path, body, conAuth = true) {
  const res = await _fetch(path, {
    method: "POST",
    headers: await _headers(conAuth),
    body: JSON.stringify(body || {}),
  });
  return _manejar(res);
}

export async function apiPut(path, body, conAuth = true) {
  const res = await _fetch(path, {
    method: "PUT",
    headers: await _headers(conAuth),
    body: JSON.stringify(body || {}),
  });
  return _manejar(res);
}

// Envío de formulario multipart (para subir el documento de la solicitud).
// No se fija Content-Type a mano: fetch añade el boundary correcto.
export async function apiPostForm(path, formData) {
  const res = await _fetch(path, { method: "POST", body: formData });
  return _manejar(res);
}

export async function apiDelete(path, conAuth = true) {
  const res = await _fetch(path, {
    method: "DELETE",
    headers: await _headers(conAuth),
  });
  // 204 sin cuerpo
  if (res.status === 204) return true;
  return _manejar(res);
}

import * as FileSystem from "expo-file-system";

// Descarga el recibo PDF (autenticado) a un archivo local y devuelve su URI.
export async function descargarReciboPDF(pagoId) {
  const t = await leerToken();
  const destino = `${FileSystem.cacheDirectory}recibo_${pagoId}.pdf`;
  const { uri } = await FileSystem.downloadAsync(
    `${API_URL}/pagos/${pagoId}/recibo.pdf`,
    destino,
    { headers: { Authorization: `Bearer ${t}` } }
  );
  return uri;
}
