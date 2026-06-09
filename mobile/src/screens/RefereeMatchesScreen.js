// Lista de partidos asignados al árbitro (modo árbitro).
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { apiGet } from "../api";
import { colors, styles } from "../theme";

export default function RefereeMatchesScreen({ navigation }) {
  const [partidos, setPartidos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const r = await apiGet("/partidos?mios=true");
      setPartidos(r);
    } catch (_) {
      setPartidos([]);
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, []);

  // Recarga cada vez que la pantalla recupera el foco (al volver del partido)
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  if (cargando) {
    return (
      <View style={styles.screen}>
        <ActivityIndicator color={colors.lime} style={{ marginTop: 40 }} />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refrescando}
          onRefresh={() => {
            setRefrescando(true);
            cargar();
          }}
          tintColor={colors.lime}
        />
      }
    >
      <Text style={[styles.muted, { marginBottom: 16 }]}>
        Partidos que tienes asignados como árbitro.
      </Text>

      {partidos.length === 0 ? (
        <Text style={styles.muted}>No tienes partidos asignados.</Text>
      ) : (
        partidos.map((p) => (
          <TouchableOpacity
            key={p.id}
            style={styles.card}
            onPress={() => navigation.navigate("RefereeLive", { partidoId: p.id })}
          >
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text style={styles.cardTitle}>
                {(p.equipo_local_nombre || "?") + "  vs  " + (p.equipo_visitante_nombre || "?")}
              </Text>
              <Text style={styles.score}>{p.goles_local}–{p.goles_visitante}</Text>
            </View>
            <Text style={styles.cardSub}>
              {(p.torneo_nombre || "Torneo")}
              {p.fecha_hora ? ` · ${p.fecha_hora.replace("T", " ").slice(0, 16)}` : ""}
            </Text>
            <Text style={[styles.pill, { marginTop: 8 }]}>{String(p.estado).replace("_", " ")}</Text>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}
