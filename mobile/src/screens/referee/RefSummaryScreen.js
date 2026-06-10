// RESUMEN DEL PARTIDO (acta): marcador final, goles, tarjetas, firma digital
// y envío del acta al sistema.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { lp, ls } from "../../publicTheme";

export default function RefSummaryScreen({ route, navigation }) {
  const { partidoId } = route.params;
  const [partido, setPartido] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [firmada, setFirmada] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [p, ev] = await Promise.all([
        apiGet(`/partidos/${partidoId}`),
        apiGet(`/partidos/${partidoId}/eventos`),
      ]);
      setPartido(p);
      setEventos(ev);
      setFirmada(!!p.acta_firmada);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar el acta");
    } finally {
      setCargando(false);
    }
  }, [partidoId]);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function enviar() {
    if (!firmada) { Alert.alert("Falta firmar", "Firma digitalmente el acta para enviarla."); return; }
    setEnviando(true);
    try {
      await apiPost(`/partidos/${partidoId}/acta`, {});
      Alert.alert("Acta enviada", "El acta se registró en el sistema.", [
        { text: "OK", onPress: () => navigation.navigate("Referee") },
      ]);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo enviar");
    } finally {
      setEnviando(false);
    }
  }

  if (cargando || !partido) {
    return <View style={ls.screen}><ActivityIndicator color={lp.maroon} style={{ marginTop: 40 }} /></View>;
  }

  const goles = eventos.filter((e) => e.tipo === "gol");
  const tarjetas = eventos.filter((e) => e.tipo.startsWith("tarjeta"));
  const yaEnviada = !!partido.acta_firmada;

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Marcador final */}
      <View style={final.card}>
        <Text style={final.label}>FINALIZADO</Text>
        <Text style={final.score}>{partido.goles_local} – {partido.goles_visitante}</Text>
        <Text style={final.teams}>{partido.equipo_local_nombre} vs {partido.equipo_visitante_nombre}</Text>
      </View>

      {/* Goles */}
      <View style={[ls.row, { flexDirection: "column", alignItems: "stretch" }]}>
        <Text style={ls.rowTitle}>Goles</Text>
        {goles.length === 0 ? <Text style={ls.muted}>Sin goles.</Text> :
          goles.map((g) => (
            <Text key={g.id} style={tx}>
              {g.minuto != null ? `${g.minuto}' ` : ""}⚽ {g.jugador_nombre || "—"}
              {g.subtipo && g.subtipo !== "normal" ? ` (${g.subtipo})` : ""}
              {g.jugador_secundario_nombre ? `  · asist. ${g.jugador_secundario_nombre}` : ""}
            </Text>
          ))}
      </View>

      {/* Tarjetas */}
      <View style={[ls.row, { flexDirection: "column", alignItems: "stretch" }]}>
        <Text style={ls.rowTitle}>Tarjetas</Text>
        {tarjetas.length === 0 ? <Text style={ls.muted}>Sin tarjetas.</Text> :
          tarjetas.map((t) => (
            <Text key={t.id} style={tx}>
              {t.minuto != null ? `${t.minuto}' ` : ""}{t.tipo === "tarjeta_roja" ? "🟥" : "🟨"} {t.jugador_nombre || "—"}
            </Text>
          ))}
      </View>

      {/* Firma */}
      <TouchableOpacity
        style={[ls.row, { alignItems: "center" }]}
        onPress={() => !yaEnviada && setFirmada(!firmada)}
        disabled={yaEnviada}
      >
        <View style={[check, (firmada || yaEnviada) && { backgroundColor: lp.green, borderColor: lp.green }]}>
          {(firmada || yaEnviada) && <Text style={{ color: lp.white, fontWeight: "800" }}>✓</Text>}
        </View>
        <Text style={[ls.rowTitle, { flex: 1 }]}>Acta firmada digitalmente</Text>
      </TouchableOpacity>

      {yaEnviada ? (
        <Text style={[ls.muted, { textAlign: "center", marginTop: 16 }]}>El acta ya fue enviada al sistema.</Text>
      ) : (
        <TouchableOpacity style={enviar_btn} onPress={enviar} disabled={enviando}>
          <Text style={{ color: lp.white, fontWeight: "800", fontSize: 15 }}>
            {enviando ? "Enviando..." : "Enviar acta al sistema"}
          </Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const final = {
  card: { backgroundColor: lp.green, borderRadius: 14, padding: 22, marginBottom: 16, alignItems: "center" },
  label: { color: lp.white, opacity: 0.85, fontWeight: "800", letterSpacing: 1.5 },
  score: { color: lp.white, fontSize: 38, fontWeight: "800", marginVertical: 6 },
  teams: { color: lp.white, opacity: 0.9 },
};
const tx = { color: lp.textDark, marginTop: 6 };
const check = { width: 26, height: 26, borderRadius: 6, borderWidth: 2, borderColor: lp.surfaceBorder, alignItems: "center", justifyContent: "center", marginRight: 12 };
const enviar_btn = { backgroundColor: lp.red, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 18 };
