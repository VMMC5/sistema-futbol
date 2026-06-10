// Pestaña PARTIDOS del árbitro: partidos asignados (programados y en juego).
// El botón "Iniciar" se desbloquea solo cuando llega la fecha/hora.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, RefreshControl, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { fechaHora } from "../../format";
import { lp, ls } from "../../publicTheme";

function yaEsHora(iso) {
  if (!iso) return true;
  const d = new Date(iso);
  return !isNaN(d.getTime()) && Date.now() >= d.getTime();
}

export default function RefMatchesScreen({ navigation }) {
  const [partidos, setPartidos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      // Asignados: programados y en juego
      const [prog, vivo] = await Promise.all([
        apiGet("/partidos?mios=true&estado=programado"),
        apiGet("/partidos?mios=true&estado=en_juego"),
      ]);
      setPartidos([...vivo, ...prog]);
    } catch (_) {
      setPartidos([]);
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function iniciar(p) {
    try {
      await apiPost(`/partidos/${p.id}/iniciar`, {});
      navigation.navigate("RefLive", { partidoId: p.id });
    } catch (e) {
      Alert.alert("No se pudo iniciar", e.message || "Intenta de nuevo");
      cargar();
    }
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.maroon} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView
      style={ls.screen}
      contentContainerStyle={ls.content}
      refreshControl={<RefreshControl refreshing={refrescando} onRefresh={() => { setRefrescando(true); cargar(); }} tintColor={lp.maroon} />}
    >
      {partidos.length === 0 ? (
        <Text style={ls.empty}>No tienes partidos asignados.</Text>
      ) : (
        partidos.map((p) => {
          const enJuego = p.estado === "en_juego";
          const desbloqueado = yaEsHora(p.fecha_hora);
          return (
            <View key={p.id} style={[ls.row, { flexDirection: "column", alignItems: "stretch" }]}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 6 }}>
                <Text style={[ls.badge, enJuego ? badgeVivo : (desbloqueado ? badgeHoy : ls.badgeNext)]}>
                  {enJuego ? "EN JUEGO" : (desbloqueado ? "HOY" : "PROGRAMADO")}
                </Text>
                <Text style={ls.rowSub}>{fechaHora(p.fecha_hora)}{p.cancha_nombre ? ` · ${p.cancha_nombre}` : ""}</Text>
              </View>
              <Text style={[ls.rowTitle, { marginBottom: 10 }]}>
                {(p.equipo_local_nombre || "?")} <Text style={ls.rowSub}>vs</Text> {(p.equipo_visitante_nombre || "?")}
              </Text>

              {enJuego ? (
                <TouchableOpacity style={btnMaroon} onPress={() => navigation.navigate("RefLive", { partidoId: p.id })}>
                  <Text style={btnMaroonText}>Continuar partido</Text>
                </TouchableOpacity>
              ) : desbloqueado ? (
                <TouchableOpacity style={btnMaroon} onPress={() => iniciar(p)}>
                  <Text style={btnMaroonText}>Iniciar partido</Text>
                </TouchableOpacity>
              ) : (
                <View style={[btnMaroon, { backgroundColor: "#D9D3C7" }]}>
                  <Text style={[btnMaroonText, { color: lp.textMuted }]}>Disponible a la hora del partido</Text>
                </View>
              )}
            </View>
          );
        })
      )}
    </ScrollView>
  );
}

const badgeVivo = { backgroundColor: lp.red, color: lp.white };
const badgeHoy = { backgroundColor: lp.maroon, color: lp.white };
const btnMaroon = { backgroundColor: lp.red, borderRadius: 10, paddingVertical: 13, alignItems: "center" };
const btnMaroonText = { color: lp.white, fontWeight: "800", fontSize: 14 };
