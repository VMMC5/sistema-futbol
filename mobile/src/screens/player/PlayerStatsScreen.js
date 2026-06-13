// MIS ESTADÍSTICAS: cajas de goles/asist/amarillas, gráfica de goles por jornada,
// minutos jugados, y filtro por torneo.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { lp, ls } from "../../publicTheme";

function Caja({ valor, etiqueta, bg, fg }) {
  return (
    <View style={[caja.box, { backgroundColor: bg }]}>
      <Text style={[caja.num, { color: fg }]}>{valor}</Text>
      <Text style={[caja.lbl, { color: fg }]}>{etiqueta}</Text>
    </View>
  );
}

export default function PlayerStatsScreen() {
  const [datos, setDatos] = useState(null);
  const [torneoSel, setTorneoSel] = useState(null); // null = todos
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async (torneoId) => {
    setCargando(true);
    try {
      const q = torneoId ? `?torneo_id=${torneoId}` : "";
      setDatos(await apiGet(`/jugador/estadisticas${q}`));
    } catch (_) {
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(torneoSel); }, [cargar, torneoSel]));

  if (cargando && !datos) {
    return <View style={ls.screen}><ActivityIndicator color={lp.green} style={{ marginTop: 40 }} /></View>;
  }
  if (!datos) {
    return <View style={[ls.screen, ls.content]}><Text style={ls.empty}>No se pudieron cargar las estadísticas.</Text></View>;
  }

  const maxGoles = Math.max(1, ...datos.por_jornada.map((j) => j.goles));

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Filtro por torneo */}
      {datos.torneos.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 14 }}>
          <TouchableOpacity style={[chip.base, torneoSel === null && chip.on]} onPress={() => setTorneoSel(null)}>
            <Text style={[chip.txt, torneoSel === null && chip.txtOn]}>Todos</Text>
          </TouchableOpacity>
          {datos.torneos.map((t) => (
            <TouchableOpacity key={t.id} style={[chip.base, torneoSel === t.id && chip.on]} onPress={() => setTorneoSel(t.id)}>
              <Text style={[chip.txt, torneoSel === t.id && chip.txtOn]}>{t.nombre}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Cajas */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 16 }}>
        <Caja valor={datos.goles} etiqueta="GOLES" bg={lp.green} fg={lp.white} />
        <Caja valor={datos.asistencias} etiqueta="ASIST." bg={lp.accent} fg={lp.white} />
        <Caja valor={datos.amarillas} etiqueta="AMAR." bg="#E6C84F" fg="#3a2f00" />
      </View>

      {/* Goles por jornada */}
      <View style={[ls.row, { flexDirection: "column", alignItems: "stretch" }]}>
        <Text style={ls.rowTitle}>Goles por jornada</Text>
        {datos.por_jornada.length === 0 ? (
          <Text style={[ls.muted, { marginTop: 6 }]}>Aún no hay partidos jugados.</Text>
        ) : (
          <View style={{ flexDirection: "row", alignItems: "flex-end", height: 120, marginTop: 14, gap: 10 }}>
            {datos.por_jornada.map((j, i) => (
              <View key={i} style={{ flex: 1, alignItems: "center" }}>
                <View style={{ width: "70%", height: Math.max(6, (j.goles / maxGoles) * 96), backgroundColor: j.goles === maxGoles ? lp.green : lp.accent, borderRadius: 6 }} />
                <Text style={{ color: lp.textMuted, fontSize: 11, marginTop: 6 }}>{j.etiqueta}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Minutos jugados */}
      <View style={[ls.row, { alignItems: "center" }]}>
        <Text style={[ls.rowTitle, { flex: 1 }]}>Minutos jugados</Text>
        <Text style={[ls.badge, { backgroundColor: lp.surface, color: lp.green, borderWidth: 1, borderColor: lp.surfaceBorder }]}>
          {datos.minutos_estimados}'
        </Text>
      </View>
      <Text style={[ls.muted, { marginTop: 6, fontSize: 12 }]}>Minutos estimados (90' por partido jugado).</Text>
    </ScrollView>
  );
}

const caja = {
  box: { flex: 1, borderRadius: 14, paddingVertical: 18, alignItems: "center", marginHorizontal: 4 },
  num: { fontSize: 28, fontWeight: "800" },
  lbl: { fontSize: 11, fontWeight: "700", letterSpacing: 1, marginTop: 2, opacity: 0.9 },
};
const chip = {
  base: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, backgroundColor: lp.surface, borderWidth: 1, borderColor: lp.surfaceBorder, marginRight: 8 },
  on: { backgroundColor: lp.green, borderColor: lp.green },
  txt: { color: lp.textDark, fontWeight: "700", fontSize: 13 },
  txtOn: { color: lp.white },
};
