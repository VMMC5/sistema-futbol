// Pestaña HISTORIAL: partidos finalizados que dirigió el árbitro.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { fecha } from "../../format";
import { lp, ls } from "../../publicTheme";

export default function RefHistoryScreen({ navigation }) {
  const [partidos, setPartidos] = useState([]);
  const [cargando, setCargando] = useState(true);

  useFocusEffect(useCallback(() => {
    (async () => {
      try {
        setPartidos(await apiGet("/partidos?mios=true&estado=finalizado"));
      } catch (_) {
        setPartidos([]);
      } finally {
        setCargando(false);
      }
    })();
  }, []));

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.maroon} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {partidos.length === 0 ? (
        <Text style={ls.empty}>Aún no has dirigido partidos.</Text>
      ) : (
        partidos.map((p) => (
          <TouchableOpacity key={p.id} style={ls.row} onPress={() => navigation.navigate("RefSummary", { partidoId: p.id })}>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>
                {p.equipo_local_nombre} {p.goles_local}–{p.goles_visitante} {p.equipo_visitante_nombre}
              </Text>
              <Text style={ls.rowSub}>
                {fecha(p.fecha_hora)}{p.acta_firmada ? " · acta enviada ✓" : " · acta pendiente"}
              </Text>
            </View>
            <Text style={{ color: lp.textMuted, fontSize: 22 }}>›</Text>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}
