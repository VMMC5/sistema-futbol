// Inicio del entrenador: tarjeta de su equipo, accesos y próximo partido.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { useAuth } from "../../auth";
import { fechaHora } from "../../format";
import { cs, lp, ls } from "../../publicTheme";

const ACCIONES = [
  { icon: "👥", label: "Mis equipos", destino: "Equipos" },
  { icon: "📝", label: "Inscribir", proximamente: true },
  { icon: "📋", label: "Alineación", destino: "LineupMatches" },
  { icon: "📅", label: "Reservar", proximamente: true },
];

export default function CoachHomeScreen({ navigation }) {
  const { usuario } = useAuth();
  const [resumen, setResumen] = useState(null);
  const [cargando, setCargando] = useState(true);

  useFocusEffect(
    useCallback(() => {
      navigation.setOptions({ title: `HOLA, ${(usuario?.nombre || "COACH").toUpperCase()}` });
      (async () => {
        try {
          setResumen(await apiGet("/equipos/resumen"));
        } catch (_) {
          setResumen(null);
        } finally {
          setCargando(false);
        }
      })();
    }, [navigation, usuario])
  );

  function tocar(a) {
    if (a.proximamente) {
      Alert.alert(a.label, "Disponible en la próxima entrega.");
    } else if (a.destino) {
      navigation.navigate(a.destino);
    }
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }

  const eq = resumen?.equipo_principal;
  const prox = resumen?.proximo_partido;

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {eq ? (
        <View style={cs.featureGold}>
          <Text style={cs.featureGoldName}>{eq.nombre}</Text>
          <Text style={cs.featureGoldMeta}>
            {eq.torneos_activos} {eq.torneos_activos === 1 ? "torneo activo" : "torneos activos"} · {eq.jugadores} jugadores
          </Text>
        </View>
      ) : (
        <TouchableOpacity style={cs.featureGold} onPress={() => navigation.navigate("Equipos")}>
          <Text style={cs.featureGoldName}>Crea tu primer equipo</Text>
          <Text style={cs.featureGoldMeta}>Toca aquí para empezar a gestionar tu plantilla.</Text>
        </TouchableOpacity>
      )}

      {/* Accesos rápidos */}
      <View style={cs.grid}>
        {ACCIONES.map((a) => (
          <TouchableOpacity key={a.label} style={cs.gridItem} onPress={() => tocar(a)}>
            <Text style={cs.gridIcon}>{a.icon}</Text>
            <Text style={cs.gridLabel}>{a.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Próximo partido */}
      {prox && (
        <>
          <Text style={ls.sectionTitle}>Próximo partido</Text>
          <View style={ls.feature}>
            <Text style={ls.teamName}>vs {prox.rival || "rival por definir"}</Text>
            <Text style={ls.featureMeta}>
              {fechaHora(prox.fecha_hora)}{prox.torneo_nombre ? ` · ${prox.torneo_nombre}` : ""}
            </Text>
          </View>
        </>
      )}
    </ScrollView>
  );
}
