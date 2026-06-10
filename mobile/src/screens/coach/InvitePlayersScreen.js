// Buscar jugadores registrados (sin equipo) e invitarlos al equipo.
import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { cs, lp, ls } from "../../publicTheme";

export default function InvitePlayersScreen({ route, navigation }) {
  const { equipoId } = route.params;
  const [buscar, setBuscar] = useState("");
  const [resultados, setResultados] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [invitados, setInvitados] = useState({}); // {jugadorId: true}

  useEffect(() => {
    navigation.setOptions({ title: "INVITAR JUGADORES" });
  }, [navigation]);

  // Búsqueda con un pequeño retardo (debounce)
  useEffect(() => {
    let activo = true;
    setCargando(true);
    const t = setTimeout(async () => {
      try {
        const r = await apiGet(`/equipos/jugadores-disponibles?buscar=${encodeURIComponent(buscar.trim())}`);
        if (activo) setResultados(r);
      } catch (_) {
        if (activo) setResultados([]);
      } finally {
        if (activo) setCargando(false);
      }
    }, 350);
    return () => { activo = false; clearTimeout(t); };
  }, [buscar]);

  async function invitar(jugador) {
    try {
      await apiPost(`/equipos/${equipoId}/invitaciones`, { jugador_id: jugador.id });
      setInvitados({ ...invitados, [jugador.id]: true });
    } catch (e) {
      Alert.alert("No se pudo invitar", e.message || "Intenta de nuevo");
    }
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content} keyboardShouldPersistTaps="handled">
      <View style={cs.field}>
        <TextInput
          style={cs.input}
          placeholder="Buscar jugador por nombre"
          placeholderTextColor={lp.textMuted}
          value={buscar}
          onChangeText={setBuscar}
          autoCapitalize="words"
        />
      </View>
      <Text style={[ls.muted, { marginBottom: 12 }]}>
        Solo aparecen jugadores registrados que no pertenecen a ningún equipo.
      </Text>

      {cargando ? (
        <ActivityIndicator color={lp.gold} style={{ marginTop: 20 }} />
      ) : resultados.length === 0 ? (
        <Text style={ls.empty}>Sin resultados.</Text>
      ) : (
        resultados.map((j) => (
          <View key={j.id} style={ls.row}>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{j.nombre}</Text>
              <Text style={ls.rowSub}>{j.correo}</Text>
            </View>
            {invitados[j.id] ? (
              <Text style={[ls.badge, ls.badgeNext]}>INVITADO</Text>
            ) : (
              <TouchableOpacity style={invitar_btn} onPress={() => invitar(j)}>
                <Text style={{ color: lp.goldText, fontWeight: "800", fontSize: 13 }}>Invitar</Text>
              </TouchableOpacity>
            )}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const invitar_btn = { backgroundColor: lp.gold, paddingHorizontal: 16, paddingVertical: 9, borderRadius: 999 };
