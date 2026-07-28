// INICIO del jugador: tarjeta de bienvenida, accesos a estadísticas y próximos
// partidos, y campanita de notificaciones en la cabecera.
import React, { useCallback, useLayoutEffect, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import Icono from "../../components/Icono";
import { useAuth } from "../../auth";
import { fechaHora } from "../../format";
import { lp, ls } from "../../publicTheme";

function Campanita({ onPress, hayNuevas }) {
  return (
    <TouchableOpacity onPress={onPress} style={{ paddingHorizontal: 14 }}>
      {/* La cabecera del panel del jugador es verde, así que la campana va en blanco. */}
      <Icono nombre="bell" size={20} color={lp.white} />
      {/* El glifo de la campana no llena el viewBox de 24 (deja aire a los lados
          y arriba), así que el punto va más adentro y más arriba que con el
          <Text> de antes para apoyarse en la esquina superior derecha real. */}
      {hayNuevas && <View style={{ position: "absolute", right: 11, top: -4, width: 10, height: 10, borderRadius: 5, backgroundColor: lp.red }} />}
    </TouchableOpacity>
  );
}

export default function PlayerHomeScreen({ navigation }) {
  const { usuario } = useAuth();
  const [proximo, setProximo] = useState(null);
  const [hayNuevas, setHayNuevas] = useState(false);
  const [cargando, setCargando] = useState(true);

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => <Campanita hayNuevas={hayNuevas} onPress={() => navigation.navigate("Notifications")} />,
    });
  }, [navigation, hayNuevas]);

  const cargar = useCallback(async () => {
    try {
      const [prox, notis] = await Promise.all([
        apiGet("/jugador/proximos-partidos"),
        apiGet("/notificaciones"),
      ]);
      setProximo(prox[0] || null);
      setHayNuevas(notis.some((n) => !n.leida));
    } catch (_) {
      setProximo(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Tarjeta de bienvenida */}
      <View style={tarjeta.card}>
        <Text style={tarjeta.hola}>Hola,</Text>
        <Text style={tarjeta.nombre}>{usuario?.nombre || "Jugador"}</Text>
        <Text style={tarjeta.rol}>JUGADOR</Text>
      </View>

      <TouchableOpacity style={btn.primary} onPress={() => navigation.navigate("PlayerStats")}>
        <Text style={btn.primaryText}>📊 Ver mis estadísticas</Text>
      </TouchableOpacity>

      <TouchableOpacity style={btn.ghost} onPress={() => navigation.navigate("PlayerCalendar")}>
        <Text style={btn.ghostText}>📅 Próximos partidos</Text>
      </TouchableOpacity>

      <Text style={[ls.sectionTitle, { marginTop: 22 }]}>Tu próximo partido</Text>
      {cargando ? (
        <ActivityIndicator color={lp.green} style={{ marginTop: 10 }} />
      ) : !proximo ? (
        <Text style={ls.muted}>No tienes partidos programados.</Text>
      ) : (
        <View style={ls.row}>
          <View style={{ flex: 1 }}>
            <Text style={ls.rowTitle}>vs {proximo.rival || "?"}</Text>
            <Text style={ls.rowSub}>
              {fechaHora(proximo.fecha_hora)}{proximo.torneo_nombre ? ` · ${proximo.torneo_nombre}` : ""}
            </Text>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const tarjeta = {
  card: { backgroundColor: lp.green, borderRadius: 16, padding: 20, marginBottom: 18 },
  hola: { color: "rgba(255,255,255,0.8)", fontSize: 14 },
  nombre: { color: lp.white, fontSize: 24, fontWeight: "800", marginTop: 2 },
  rol: { color: lp.accent, fontWeight: "800", letterSpacing: 1, marginTop: 8, fontSize: 12 },
};
const btn = {
  primary: { backgroundColor: lp.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginBottom: 10 },
  primaryText: { color: lp.white, fontWeight: "800", fontSize: 15 },
  ghost: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  ghostText: { color: lp.green, fontWeight: "800", fontSize: 15 },
};
