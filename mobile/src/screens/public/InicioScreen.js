// Pestaña INICIO (pública): próximos partidos.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from "react-native";
import { apiGet } from "../../api";
import { fechaHora } from "../../format";
import { lp, ls } from "../../publicTheme";

export default function InicioScreen() {
  const [partidos, setPartidos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const r = await apiGet("/publico/inicio", false);
      setPartidos(r.proximos_partidos || []);
    } catch (_) {
      setPartidos([]);
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.accent} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView
      style={ls.screen}
      contentContainerStyle={ls.content}
      refreshControl={<RefreshControl refreshing={refrescando} onRefresh={() => { setRefrescando(true); cargar(); }} tintColor={lp.accent} />}
    >
      <Text style={ls.sectionTitle}>Próximos partidos</Text>

      {partidos.length === 0 ? (
        <Text style={ls.empty}>No hay partidos próximos.</Text>
      ) : (
        partidos.map((p) => (
          <View key={p.id} style={ls.feature}>
            <Text style={ls.featureLabel}>Próximo partido</Text>
            <Text style={ls.featureMeta}>
              {fechaHora(p.fecha_hora)}{p.cancha_nombre ? ` · ${p.cancha_nombre}` : ""}
            </Text>
            <View style={ls.matchRow}>
              <Text style={ls.teamName}>{p.equipo_local_nombre || "?"}</Text>
              <Text style={ls.vs}>VS</Text>
              <Text style={ls.teamName}>{p.equipo_visitante_nombre || "?"}</Text>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}
