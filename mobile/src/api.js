// Cliente de la API + manejo del token.
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

// La URL de la API se lee de app.json (extra.apiUrl). CAMBIALA por la IP de tu PC.
export const API_URL =
  Constants.expoConfig?.extra?.apiUrl || "http://192.168.100.9:8000";

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
  const res = await fetch(`${API_URL}${path}`, { headers: await _headers(conAuth) });
  return _manejar(res);
}

export async function apiPost(path, body, conAuth = true) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: await _headers(conAuth),
    body: JSON.stringify(body || {}),
  });
  return _manejar(res);
}

// Envío de formulario multipart (para subir el documento de la solicitud).
// No se fija Content-Type a mano: fetch añade el boundary correcto.
export async function apiPostForm(path, formData) {
  const res = await fetch(`${API_URL}${path}`, { method: "POST", body: formData });
  return _manejar(res);
}

export async function apiDelete(path, conAuth = true) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    headers: await _headers(conAuth),
  });
  // 204 sin cuerpo
  if (res.status === 204) return true;
  return _manejar(res);
}
