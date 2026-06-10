// Invitaciones recibidas por el jugador (su bandeja). Aceptar o rechazar.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../api";
import { colors, styles } from "../theme";

export default function InvitationsScreen() {
  const [invitaciones, setInvitaciones] = useState([]);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      setInvitaciones(await apiGet("/invitaciones/mias"));
    } catch (_) {
      setInvitaciones([]);
    } finally {
      setCargando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function responder(inv, accion) {
    try {
      await apiPost(`/invitaciones/${inv.id}/${accion}`, {});
      setInvitaciones((prev) => prev.filter((i) => i.id !== inv.id));
      if (accion === "aceptar") {
        Alert.alert("¡Listo!", `Ahora eres parte de ${inv.equipo_nombre}.`);
      }
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo responder");
      cargar();
    }
  }

  if (cargando) {
    return <View style={styles.screen}><ActivityIndicator color={colors.lime} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={[styles.muted, { marginBottom: 16 }]}>
        Invitaciones para unirte a un equipo.
      </Text>

      {invitaciones.length === 0 ? (
        <Text style={[styles.muted, { textAlign: "center", marginTop: 30 }]}>No tienes invitaciones pendientes.</Text>
      ) : (
        invitaciones.map((inv) => (
          <View key={inv.id} style={styles.card}>
            <Text style={styles.cardTitle}>{inv.equipo_nombre}</Text>
            <Text style={styles.cardSub}>
              {inv.entrenador_nombre ? `${inv.entrenador_nombre} te invitó a unirte.` : "Te invitaron a unirte."}
            </Text>
            <View style={{ flexDirection: "row", gap: 10, marginTop: 14 }}>
              <TouchableOpacity style={[styles.btn, { flex: 1, marginTop: 0 }]} onPress={() => responder(inv, "aceptar")}>
                <Text style={styles.btnText}>Aceptar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btnGhost, { flex: 1, marginTop: 0 }]} onPress={() => responder(inv, "rechazar")}>
                <Text style={[styles.btnGhostText, { color: colors.danger }]}>Rechazar</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}
