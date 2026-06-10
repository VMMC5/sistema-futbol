// Lista de próximos partidos del entrenador, para elegir a cuál definir alineación.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { fechaHora } from "../../format";
import { cs, lp, ls } from "../../publicTheme";

export default function LineupMatchesScreen({ navigation }) {
  const [partidos, setPartidos] = useState([]);
  const [cargando, setCargando] = useState(true);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        try {
          setPartidos(await apiGet("/equipos/mis-partidos"));
        } catch (_) {
          setPartidos([]);
        } finally {
          setCargando(false);
        }
      })();
    }, [])
  );

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      <Text style={[ls.muted, { marginBottom: 14 }]}>
        Elige un partido programado para definir tu alineación.
      </Text>

      {cargando ? (
        <ActivityIndicator color={lp.gold} style={{ marginTop: 30 }} />
      ) : partidos.length === 0 ? (
        <Text style={ls.empty}>No tienes partidos programados.</Text>
      ) : (
        partidos.map((p) => (
          <TouchableOpacity
            key={p.id}
            style={ls.row}
            onPress={() => navigation.navigate("Lineup", {
              partidoId: p.id, equipoId: p.mi_equipo_id, rival: p.rival_nombre,
            })}
          >
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{p.mi_equipo_nombre} vs {p.rival_nombre || "rival"}</Text>
              <Text style={ls.rowSub}>
                {fechaHora(p.fecha_hora)}{p.torneo_nombre ? ` · ${p.torneo_nombre}` : ""}
              </Text>
            </View>
            <Text style={cs.chevron}>›</Text>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}
