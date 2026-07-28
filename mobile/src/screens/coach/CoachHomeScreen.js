// Inicio del entrenador: tarjeta de su equipo, accesos y próximo partido.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { useAuth } from "../../auth";
import Icono from "../../components/Icono";
import { fechaHora } from "../../format";
import { cs, lp, ls } from "../../publicTheme";

const ACCIONES = [
  { icono: "people", label: "Mis equipos", destino: "Equipos" },
  { icono: "docadd", label: "Inscribir", proximamente: true },
  { icono: "clipboardlist", label: "Alineación", destino: "LineupMatches" },
  { icono: "calendar", label: "Reservar", proximamente: true },
];

export default function CoachHomeScreen({ navigation }) {
  const { usuario } = useAuth();
  const [resumen, setResumen] = useState(null);
  const [cargando, setCargando] = useState(true);

  // No se toca el título: la pestaña y la cabecera dicen "INICIO" desde App.js,
  // igual que en el panel del jugador. El saludo vive en la tarjeta de abajo.
  useFocusEffect(
    useCallback(() => {
      (async () => {
        try {
          setResumen(await apiGet("/equipos/resumen"));
        } catch (_) {
          setResumen(null);
        } finally {
          setCargando(false);
        }
      })();
    }, [])
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
      {/* Saludo: antes estaba en la cabecera y truncaba la etiqueta de la pestaña. */}
      <View style={saludo.card}>
        <Text style={saludo.hola}>Hola,</Text>
        <Text style={saludo.nombre}>{usuario?.nombre || "Entrenador"}</Text>
        <Text style={saludo.rol}>ENTRENADOR</Text>
      </View>

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
            <View style={{ marginBottom: 8 }}><Icono nombre={a.icono} size={24} color={lp.gold} /></View>
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

// Tarjeta de saludo. Va en claro y no en dorado a propósito: la tarjeta del
// equipo, justo debajo, ya es dorada, y dos bloques dorados seguidos se leen
// como una sola mancha. La insignia de rol conserva el dorado del panel.
const saludo = {
  card: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 16, padding: 20, marginBottom: 16 },
  hola: { color: lp.textMuted, fontSize: 14 },
  nombre: { color: lp.textDark, fontSize: 24, fontWeight: "800", marginTop: 2 },
  rol: { color: lp.gold, fontWeight: "800", letterSpacing: 1, marginTop: 8, fontSize: 12 },
};
