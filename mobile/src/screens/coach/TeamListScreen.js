// Listado de equipos del entrenador.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { cs, lp, ls } from "../../publicTheme";

const COLORES = ["#2E7D52", "#1F6FB2", "#C0392B", "#8A6D1E", "#6B4FA0"];

export default function TeamListScreen({ navigation }) {
  const [equipos, setEquipos] = useState([]);
  const [cargando, setCargando] = useState(true);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        try {
          setEquipos(await apiGet("/equipos"));
        } catch (_) {
          setEquipos([]);
        } finally {
          setCargando(false);
        }
      })();
    }, [])
  );

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {cargando ? (
        <ActivityIndicator color={lp.gold} style={{ marginTop: 30 }} />
      ) : equipos.length === 0 ? (
        <Text style={ls.empty}>Aún no tienes equipos. Crea el primero abajo.</Text>
      ) : (
        equipos.map((e, i) => (
          <TouchableOpacity key={e.id} style={ls.row} onPress={() => navigation.navigate("TeamStats", { equipoId: e.id })}>
            <View style={[cs.avatar, { backgroundColor: COLORES[i % COLORES.length] }]}>
              <Text style={cs.avatarText}>{(e.nombre || "?").charAt(0).toUpperCase()}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{e.nombre}</Text>
              <Text style={ls.rowSub}>
                {e.jugadores_count} jugadores{e.categoria ? ` · ${e.categoria}` : ""}
              </Text>
            </View>
            <Text style={cs.chevron}>›</Text>
          </TouchableOpacity>
        ))
      )}

      <TouchableOpacity style={cs.primaryBtn} onPress={() => navigation.navigate("TeamEdit", {})}>
        <Text style={cs.primaryBtnText}>+ Crear nuevo equipo</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
