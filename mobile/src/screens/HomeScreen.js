// Panel tras iniciar sesión. Muestra contenido según el rol del usuario.
import React, { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../api";
import { useAuth } from "../auth";
import { colors, styles } from "../theme";

const MENSAJE_ROL = {
  jugador: "Consulta torneos, tablas de posiciones y tus próximos partidos.",
  entrenador: "Gestiona tu equipo, inscríbelo a torneos y arma las alineaciones.",
  arbitro: "Aquí verás los partidos que te asignen para dirigir y registrar eventos.",
  superadmin: "Tienes acceso completo. La administración detallada está en el panel web.",
};

export default function HomeScreen({ navigation }) {
  const { usuario, logout } = useAuth();
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setDatos(await apiGet("/publico/inicio", false));
      } catch (_) {
        setDatos({ proximos_partidos: [] });
      } finally {
        setCargando(false);
      }
    })();
  }, []);

  async function salir() {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: "Public" }] });
  }

  const rol = usuario?.rol || "jugador";

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.muted}>Hola,</Text>
      <Text style={styles.h1}>{usuario?.nombre || "Usuario"}</Text>
      <Text style={[styles.pill, { marginTop: 10, marginBottom: 18 }]}>{rol}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Tu panel</Text>
        <Text style={styles.cardSub}>{MENSAJE_ROL[rol] || ""}</Text>
      </View>

      {(rol === "arbitro" || rol === "superadmin") && (
        <TouchableOpacity
          style={[styles.btn, { marginBottom: 8 }]}
          onPress={() => navigation.navigate("RefereeMatches")}
        >
          <Text style={styles.btnText}>🟢 Modo árbitro (partidos en vivo)</Text>
        </TouchableOpacity>
      )}

      {rol === "jugador" && (
        <TouchableOpacity
          style={[styles.btn, { marginBottom: 8 }]}
          onPress={() => navigation.navigate("Invitations")}
        >
          <Text style={styles.btnText}>📨 Mis invitaciones a equipos</Text>
        </TouchableOpacity>
      )}

      <Text style={styles.h2}>Próximos partidos</Text>
      {cargando ? (
        <ActivityIndicator color={colors.lime} />
      ) : datos.proximos_partidos.length === 0 ? (
        <Text style={styles.muted}>No hay partidos programados.</Text>
      ) : (
        datos.proximos_partidos.map((p) => (
          <View key={p.id} style={styles.card}>
            <Text style={styles.cardTitle}>
              {(p.equipo_local_nombre || "?") + "  vs  " + (p.equipo_visitante_nombre || "?")}
            </Text>
            <Text style={styles.cardSub}>
              {(p.torneo_nombre || "Torneo")}
              {p.fecha_hora ? ` · ${p.fecha_hora.replace("T", " ").slice(0, 16)}` : ""}
            </Text>
          </View>
        ))
      )}

      <TouchableOpacity style={[styles.btnGhost, { marginTop: 24 }]} onPress={salir}>
        <Text style={styles.btnGhostText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
