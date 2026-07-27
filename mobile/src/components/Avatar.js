// Foto de perfil con fallback a la inicial del nombre cuando no hay foto,
// no hay token todavía, o la descarga falla.
//
// La foto está protegida con JWT. React Native <Image source={{uri, headers}}>
// NO envía la cabecera Authorization de forma fiable (el GET llega sin token y
// el servidor responde 401), así que se descarga con FileSystem.downloadAsync
// —que SÍ respeta los headers, igual que el recibo PDF— a un archivo local y se
// muestra ese archivo.
import React, { useEffect, useState } from "react";
import { Image, Text, View } from "react-native";
import * as FileSystem from "expo-file-system";
import { urlFoto, leerToken } from "../api";

export default function Avatar({ usuarioId, nombre, size = 36, version }) {
  const [uri, setUri] = useState(null);

  useEffect(() => {
    let vivo = true;
    setUri(null);  // al cambiar de usuario o versión, se muestra la inicial mientras baja
    (async () => {
      if (!usuarioId) return;
      try {
        const token = await leerToken();
        if (!token) return;
        // La versión va en el nombre del archivo: al reemplazar la foto cambia el
        // destino y se descarga la nueva en vez de reusar la cacheada.
        const destino = `${FileSystem.cacheDirectory}avatar_${usuarioId}_${version ?? "x"}.jpg`;
        const { uri: local, status } = await FileSystem.downloadAsync(
          urlFoto(usuarioId), destino, { headers: { Authorization: `Bearer ${token}` } },
        );
        // Solo un 200 es una imagen; 401/404 dejan `local` con el cuerpo de error.
        if (vivo && status === 200) setUri(local);
      } catch {
        // red caída o sin foto: se queda en la inicial
      }
    })();
    return () => { vivo = false; };
  }, [usuarioId, version]);

  const inicial = (nombre || "?").charAt(0).toUpperCase();
  const base = { width: size, height: size, borderRadius: size * 0.25 };

  if (!uri) {
    return (
      <View style={[base, { backgroundColor: "#31513d", alignItems: "center", justifyContent: "center",
                            borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]}>
        <Text style={{ color: "#dfe9e2", fontWeight: "700" }}>{inicial}</Text>
      </View>
    );
  }
  return (
    <Image source={{ uri }} style={[base, { borderWidth: 1, borderColor: "rgba(255,255,255,0.3)" }]} />
  );
}
