// Vista de alineaciones del árbitro: descarga ambos planes y el resumen por
// jugador, y deja alternar entre local y visitante sobre la cancha.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { lp, ls } from "../../publicTheme";
import LineupPitch from "../../components/LineupPitch";

export default function RefLineupScreen({ route, navigation }) {
  const { partidoId } = route.params;

  const [partido, setPartido] = useState(null);
  const [planes, setPlanes] = useState({}); // {equipoId: {formacion, jugadores, suplentes, nombre}}
  const [resumen, setResumen] = useState({}); // {"<jugador_id>": {...}}
  const [equipoSel, setEquipoSel] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      const p = await apiGet(`/partidos/${partidoId}`);
      setPartido(p);
      setEquipoSel((actual) => actual || p.equipo_local_id);

      const mapa = {};
      for (const [id, nombre] of [[p.equipo_local_id, p.equipo_local_nombre], [p.equipo_visitante_id, p.equipo_visitante_nombre]]) {
        if (!id) continue;
        try {
          const plan = await apiGet(`/partidos/${partidoId}/plan?equipo_id=${id}`);
          mapa[id] = { nombre, ...plan };
        } catch (_) { mapa[id] = { nombre, formacion: null, jugadores: [], suplentes: [] }; }
      }
      setPlanes(mapa);

      try {
        const r = await apiGet(`/partidos/${partidoId}/resumen-jugadores`);
        setResumen(r || {});
      } catch (_) { setResumen({}); }
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar");
    } finally {
      setCargando(false);
    }
  }, [partidoId]);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  if (cargando || !partido) {
    return <View style={ls.screen}><ActivityIndicator color={lp.maroon} style={{ marginTop: 40 }} /></View>;
  }

  const equipos = [partido.equipo_local_id, partido.equipo_visitante_id].filter(Boolean);
  const plan = planes[equipoSel] || null;

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Selector de equipo */}
      <View style={ls.tabs}>
        {equipos.map((id) => (
          <TouchableOpacity
            key={id}
            style={[ls.tab, equipoSel === id && { backgroundColor: lp.green }]}
            onPress={() => setEquipoSel(id)}
          >
            <Text style={[ls.tabText, equipoSel === id && ls.tabTextActive]}>
              {planes[id]?.nombre || "Equipo"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <LineupPitch equipoId={equipoSel} plan={plan} resumen={resumen} />
    </ScrollView>
  );
}
