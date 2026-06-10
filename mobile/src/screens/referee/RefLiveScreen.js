// PARTIDO EN VIVO: marcador, botones de eventos (gol/amarilla/roja/cambio),
// caja con los eventos registrados y botón de finalizar.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { lp, ls } from "../../publicTheme";

const ICONO = { gol: "⚽", tarjeta_amarilla: "🟨", tarjeta_roja: "🟥", cambio: "🔁" };

function resumenEvento(e) {
  const min = e.minuto != null ? `${e.minuto}' ` : "";
  if (e.tipo === "gol") {
    const extra = e.subtipo && e.subtipo !== "normal" ? ` (${e.subtipo})` : "";
    return `${min}⚽ ${e.jugador_nombre || "Gol"}${extra}`;
  }
  if (e.tipo === "cambio") return `${min}🔁 ${e.jugador_secundario_nombre || "?"} por ${e.jugador_nombre || "?"}`;
  return `${min}${ICONO[e.tipo] || ""} ${e.jugador_nombre || ""}`;
}

export default function RefLiveScreen({ route, navigation }) {
  const { partidoId } = route.params;
  const [partido, setPartido] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      const [p, ev] = await Promise.all([
        apiGet(`/partidos/${partidoId}`),
        apiGet(`/partidos/${partidoId}/eventos`),
      ]);
      setPartido(p);
      setEventos(ev);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar");
    } finally {
      setCargando(false);
    }
  }, [partidoId]);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  function abrirEvento(tipo) {
    navigation.navigate("RefEvent", { partidoId, tipo });
  }

  function finalizar() {
    Alert.alert("Finalizar partido", "¿Finalizar el partido y pasar al acta?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Finalizar", style: "destructive", onPress: async () => {
        try {
          await apiPost(`/partidos/${partidoId}/finalizar`, {});
          navigation.navigate("RefSummary", { partidoId });
        } catch (e) { Alert.alert("Error", e.message); }
      }},
    ]);
  }

  if (cargando || !partido) {
    return <View style={ls.screen}><ActivityIndicator color={lp.maroon} style={{ marginTop: 40 }} /></View>;
  }

  if (partido.estado === "finalizado") {
    return (
      <View style={[ls.screen, ls.content]}>
        <Text style={ls.empty}>El partido ya finalizó.</Text>
        <TouchableOpacity style={[btn.full, { backgroundColor: lp.red }]} onPress={() => navigation.navigate("RefSummary", { partidoId })}>
          <Text style={btn.fullText}>Ver acta</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Marcador */}
      <View style={marcador.card}>
        <Text style={marcador.team}>{partido.equipo_local_nombre || "Local"}</Text>
        <Text style={marcador.score}>{partido.goles_local} – {partido.goles_visitante}</Text>
        <Text style={marcador.team}>{partido.equipo_visitante_nombre || "Visitante"}</Text>
      </View>

      {/* Botones de evento 2x2 */}
      <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" }}>
        {[
          { tipo: "gol", label: "Gol", bg: lp.green, fg: lp.white },
          { tipo: "tarjeta_amarilla", label: "Amarilla", bg: "#E6C84F", fg: "#3a2f00" },
          { tipo: "tarjeta_roja", label: "Roja", bg: lp.red, fg: lp.white },
          { tipo: "cambio", label: "Cambio", bg: lp.surface, fg: lp.textDark, borde: true },
        ].map((b) => (
          <TouchableOpacity
            key={b.tipo}
            style={[evBtn.box, { backgroundColor: b.bg }, b.borde && { borderWidth: 1, borderColor: lp.surfaceBorder }]}
            onPress={() => abrirEvento(b.tipo)}
          >
            <Text style={[evBtn.icon]}>{ICONO[b.tipo]}</Text>
            <Text style={[evBtn.label, { color: b.fg }]}>{b.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Caja de eventos */}
      <View style={[ls.row, { flexDirection: "column", alignItems: "stretch", marginTop: 14 }]}>
        {eventos.length === 0 ? (
          <Text style={ls.muted}>Aún no hay eventos registrados.</Text>
        ) : (
          eventos.map((e) => (
            <Text key={e.id} style={{ color: lp.textDark, marginVertical: 3 }}>{resumenEvento(e)}</Text>
          ))
        )}
      </View>

      <TouchableOpacity style={[btn.full, { backgroundColor: lp.red, marginTop: 16 }]} onPress={finalizar}>
        <Text style={btn.fullText}>Finalizar partido</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const marcador = {
  card: { backgroundColor: lp.maroon, borderRadius: 14, padding: 18, marginBottom: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  team: { color: lp.white, fontSize: 14, fontWeight: "700", flex: 1, textAlign: "center" },
  score: { color: lp.white, fontSize: 34, fontWeight: "800", paddingHorizontal: 8 },
};
const evBtn = {
  box: { width: "48%", borderRadius: 14, paddingVertical: 22, alignItems: "center", marginBottom: 12 },
  icon: { fontSize: 22, marginBottom: 6 },
  label: { fontWeight: "800", fontSize: 15 },
};
const btn = {
  full: { borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  fullText: { color: lp.white, fontWeight: "800", fontSize: 15 },
};
