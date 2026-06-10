// Estadísticas de un equipo: récord, posición y goleadores.
import React, { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { cs, lp, ls } from "../../publicTheme";

const CAJAS = [
  { key: "pj", label: "PJ", bg: "#E6C84F", fg: "#3a2f00" },
  { key: "pg", label: "PG", bg: "#2E7D52", fg: "#fff" },
  { key: "pe", label: "PE", bg: "#123D2A", fg: "#fff" },
  { key: "pp", label: "PP", bg: "#C0392B", fg: "#fff" },
];

export default function TeamStatsScreen({ route, navigation }) {
  const { equipoId } = route.params;
  const [data, setData] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const d = await apiGet(`/equipos/${equipoId}/estadisticas`);
        setData(d);
        navigation.setOptions({ title: `ESTADÍSTICAS · ${(d.equipo?.nombre || "").toUpperCase()}` });
      } catch (_) {
        setData(null);
      } finally {
        setCargando(false);
      }
    })();
  }, [equipoId]);

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }
  if (!data) {
    return <View style={ls.screen}><Text style={ls.empty}>No se pudieron cargar las estadísticas.</Text></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Cajas PJ/PG/PE/PP */}
      <View style={cs.statsRow}>
        {CAJAS.map((c) => (
          <View key={c.key} style={[cs.statBox, { backgroundColor: c.bg }]}>
            <Text style={[cs.statNum, { color: c.fg }]}>{data[c.key]}</Text>
            <Text style={[cs.statLabel, { color: c.fg }]}>{c.label}</Text>
          </View>
        ))}
      </View>

      {/* Posición en liga */}
      <View style={[ls.row, { justifyContent: "space-between" }]}>
        <View>
          <Text style={ls.rowTitle}>Posición en liga</Text>
          {data.torneo_nombre ? <Text style={ls.rowSub}>{data.torneo_nombre}</Text> : null}
        </View>
        <Text style={[ls.pts, { color: lp.gold, fontSize: 18 }]}>
          {data.posicion ? `${data.posicion}º` : "—"}
        </Text>
      </View>

      {/* Goleadores */}
      <Text style={ls.sectionTitle}>Goleadores</Text>
      {data.goleadores.length === 0 ? (
        <Text style={ls.empty}>Aún no hay goles registrados.</Text>
      ) : (
        data.goleadores.map((g, i) => (
          <View key={g.jugador_id} style={ls.standRow}>
            <Text style={ls.rank}>{i + 1}</Text>
            <Text style={[ls.rowTitle, { flex: 1 }]}>{g.nombre}</Text>
            <Text style={ls.pts}>{g.goles} {g.goles === 1 ? "gol" : "goles"}</Text>
          </View>
        ))
      )}

      <TouchableOpacity style={cs.primaryBtn} onPress={() => navigation.navigate("TeamEdit", { equipoId })}>
        <Text style={cs.primaryBtnText}>Editar equipo y plantilla</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
