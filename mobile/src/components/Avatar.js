// Foto de perfil con fallback a la inicial del nombre cuando no hay foto,
// no hay token todavía, o la descarga falla.
import React, { useEffect, useState } from "react";
import { Image, Text, View } from "react-native";
import { urlFoto, leerToken } from "../api";
import { lp } from "../publicTheme";

export default function Avatar({ usuarioId, nombre, size = 36 }) {
  const [token, setToken] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => { leerToken().then(setToken); }, []);

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
  return (
    <Image
      source={{ uri: urlFoto(usuarioId), headers: { Authorization: `Bearer ${token}` } }}
      style={[base, { borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]}
      onError={() => setError(true)}
    />
  );
}
