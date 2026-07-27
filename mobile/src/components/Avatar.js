// Foto de perfil con fallback a la inicial del nombre cuando no hay foto,
// no hay token todavía, o la descarga falla.
import React, { useEffect, useState } from "react";
import { Image, Text, View } from "react-native";
import { urlFoto, leerToken } from "../api";
import { lp } from "../publicTheme";

export default function Avatar({ usuarioId, nombre, size = 36, version }) {
  const [token, setToken] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => { leerToken().then(setToken); }, []);

  // Reintenta la foto cuando cambia el usuario (p. ej. al alternar pestañas de
  // equipos, donde la misma instancia de Avatar cambia de usuarioId) o cuando
  // `version` cambia (tras subir/reemplazar la foto propia): sin esto, un 404
  // previo dejaría el error pegado y se seguiría mostrando la inicial.
  useEffect(() => { setError(false); }, [usuarioId, version]);

  const inicial = (nombre || "?").charAt(0).toUpperCase();
  const base = { width: size, height: size, borderRadius: size * 0.25 };

  if (!usuarioId || error || !token) {
    return (
      <View style={[base, { backgroundColor: "#31513d", alignItems: "center", justifyContent: "center",
                            borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]}>
        <Text style={{ color: "#dfe9e2", fontWeight: "700" }}>{inicial}</Text>
      </View>
    );
  }
  // `version` cambia en cada subida; al ir en la URL, sortea la caché por-URI de
  // RN Image y muestra la foto nueva en vez de los bytes viejos cacheados.
  const uri = version != null ? `${urlFoto(usuarioId)}?v=${version}` : urlFoto(usuarioId);
  return (
    <Image
      source={{ uri, headers: { Authorization: `Bearer ${token}` } }}
      style={[base, { borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]}
      onError={() => setError(true)}
    />
  );
}
