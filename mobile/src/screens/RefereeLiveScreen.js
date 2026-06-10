// Modo árbitro EN VIVO: marcador, registro de eventos (goles/tarjetas) y control
// del partido (iniciar / finalizar). Solo el árbitro asignado puede operar.
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { apiGet, apiPost, apiDelete } from "../api";
import { colors, styles } from "../theme";

const TIPOS = [
  { tipo: "gol", etiqueta: "⚽ Gol", color: colors.lime, texto: colors.pitch900 },
  { tipo: "tarjeta_amarilla", etiqueta: "🟨 Amarilla", color: "#ffce5a", texto: "#1a1500" },
  { tipo: "tarjeta_roja", etiqueta: "🟥 Roja", color: colors.danger, texto: "#fff" },
  { tipo: "cambio", etiqueta: "🔁 Cambio", color: colors.pitch600, texto: colors.chalk },
];

export default function RefereeLiveScreen({ route }) {
  const { partidoId } = route.params;
  const [partido, setPartido] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [planes, setPlanes] = useState({}); // { equipoId: [ {jugador_id, nombre, dorsal} ] }
  const [cargando, setCargando] = useState(true);
  const [ocupado, setOcupado] = useState(false);

  // Selección actual para registrar un evento
  const [equipoSel, setEquipoSel] = useState(null);
  const [jugadorSel, setJugadorSel] = useState(null);
  const [minuto, setMinuto] = useState("");

  const cargar = useCallback(async () => {
    try {
      const [p, ev] = await Promise.all([
        apiGet(`/partidos/${partidoId}`),
        apiGet(`/partidos/${partidoId}/eventos`),
      ]);
      setPartido(p);
      setEventos(ev);
      setEquipoSel((actual) => actual || p.equipo_local_id);

      // Alineación que armó el entrenador para cada equipo (unificación)
      const nuevos = {};
      for (const eqId of [p.equipo_local_id, p.equipo_visitante_id]) {
        if (!eqId) continue;
        try {
          const plan = await apiGet(`/partidos/${partidoId}/plan?equipo_id=${eqId}`);
          nuevos[eqId] = (plan.jugadores || []).filter((j) => j.jugador_id != null);
        } catch (_) {
          nuevos[eqId] = [];
        }
      }
      setPlanes(nuevos);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar el partido");
    } finally {
      setCargando(false);
    }
  }, [partidoId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  // Mientras el partido está en juego, refresca el marcador cada 6s.
  useEffect(() => {
    if (partido?.estado !== "en_juego") return;
    const t = setInterval(cargar, 6000);
    return () => clearInterval(t);
  }, [partido?.estado, cargar]);

  async function accion(fn) {
    if (ocupado) return;
    setOcupado(true);
    try {
      await fn();
      await cargar();
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo completar la acción");
    } finally {
      setOcupado(false);
    }
  }

  const iniciar = () => accion(() => apiPost(`/partidos/${partidoId}/iniciar`, {}));

  const finalizar = () =>
    Alert.alert("Finalizar partido", "¿Seguro que quieres finalizar el partido?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Finalizar", style: "destructive", onPress: () => accion(() => apiPost(`/partidos/${partidoId}/finalizar`, {})) },
    ]);

  const registrar = (tipo) =>
    accion(async () => {
      const cuerpo = { tipo, equipo_id: equipoSel };
      if (jugadorSel) cuerpo.jugador_id = jugadorSel;
      const m = parseInt(minuto, 10);
      if (!Number.isNaN(m)) cuerpo.minuto = m;
      await apiPost(`/partidos/${partidoId}/eventos`, cuerpo);
      setJugadorSel(null); // listo para el siguiente
    });

  const borrarEvento = (eid) =>
    Alert.alert("Eliminar evento", "¿Borrar este evento? El marcador se ajustará.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Borrar", style: "destructive", onPress: () => accion(() => apiDelete(`/partidos/${partidoId}/eventos/${eid}`)) },
    ]);

  if (cargando || !partido) {
    return (
      <View style={styles.screen}>
        <ActivityIndicator color={colors.lime} style={{ marginTop: 40 }} />
      </View>
    );
  }

  const enJuego = partido.estado === "en_juego";
  const jugadoresEquipo = planes[equipoSel] || [];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {/* Marcador */}
      <View style={styles.card}>
        <View style={live.scoreRow}>
          <Text style={live.teamName}>{partido.equipo_local_nombre || "Local"}</Text>
          <Text style={live.scoreBig}>{partido.goles_local} : {partido.goles_visitante}</Text>
          <Text style={live.teamName}>{partido.equipo_visitante_nombre || "Visitante"}</Text>
        </View>
        <Text style={[styles.pill, { alignSelf: "center", marginTop: 10 }]}>
          {String(partido.estado).replace("_", " ")}
        </Text>
      </View>

      {/* Control según estado */}
      {partido.estado === "programado" && (
        <TouchableOpacity style={styles.btn} onPress={iniciar} disabled={ocupado}>
          <Text style={styles.btnText}>▶ Iniciar partido</Text>
        </TouchableOpacity>
      )}

      {partido.estado === "finalizado" && (
        <Text style={[styles.muted, { textAlign: "center", marginVertical: 10 }]}>
          Partido finalizado. Marcador final {partido.goles_local}–{partido.goles_visitante}.
        </Text>
      )}

      {enJuego && (
        <>
          {/* Selección de equipo */}
          <Text style={styles.label}>Equipo</Text>
          <View style={{ flexDirection: "row", gap: 10, marginBottom: 12 }}>
            {[
              { id: partido.equipo_local_id, nombre: partido.equipo_local_nombre || "Local" },
              { id: partido.equipo_visitante_id, nombre: partido.equipo_visitante_nombre || "Visitante" },
            ].map((eq) => (
              <TouchableOpacity
                key={eq.id}
                onPress={() => { setEquipoSel(eq.id); setJugadorSel(null); }}
                style={[live.seg, equipoSel === eq.id && { backgroundColor: colors.lime, borderColor: colors.lime }]}
              >
                <Text style={[live.segText, equipoSel === eq.id && { color: colors.pitch900 }]}>{eq.nombre}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Minuto */}
          <Text style={styles.label}>Minuto (opcional)</Text>
          <TextInput
            style={styles.input}
            keyboardType="number-pad"
            placeholder="Ej. 45"
            placeholderTextColor={colors.muted}
            value={minuto}
            onChangeText={setMinuto}
          />

          {/* Jugador (de la alineación que armó el entrenador) */}
          <Text style={styles.label}>Jugador (opcional)</Text>
          {jugadoresEquipo.length === 0 ? (
            <Text style={[styles.muted, { marginBottom: 12 }]}>
              El entrenador no ha cargado la alineación de este equipo. Puedes registrar el evento sin jugador.
            </Text>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
              {jugadoresEquipo.map((j) => (
                <TouchableOpacity
                  key={j.jugador_id}
                  onPress={() => setJugadorSel(jugadorSel === j.jugador_id ? null : j.jugador_id)}
                  style={[live.chip, jugadorSel === j.jugador_id && { backgroundColor: colors.lime, borderColor: colors.lime }]}
                >
                  <Text style={[live.chipText, jugadorSel === j.jugador_id && { color: colors.pitch900 }]}>
                    {j.dorsal != null ? `#${j.dorsal} ` : ""}{j.nombre || `Jugador ${j.jugador_id}`}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          )}

          {/* Botones de evento */}
          <View style={live.grid}>
            {TIPOS.map((t) => (
              <TouchableOpacity
                key={t.tipo}
                style={[live.evBtn, { backgroundColor: t.color }]}
                onPress={() => registrar(t.tipo)}
                disabled={ocupado}
              >
                <Text style={[live.evBtnText, { color: t.texto }]}>{t.etiqueta}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity style={[styles.btnGhost, { marginTop: 16 }]} onPress={finalizar} disabled={ocupado}>
            <Text style={[styles.btnGhostText, { color: colors.danger }]}>⏹ Finalizar partido</Text>
          </TouchableOpacity>
        </>
      )}

      {/* Eventos registrados */}
      <Text style={[styles.h2, { marginTop: 22 }]}>Eventos</Text>
      {eventos.length === 0 ? (
        <Text style={styles.muted}>Aún no hay eventos.</Text>
      ) : (
        eventos.map((e) => (
          <View key={e.id} style={[styles.card, { flexDirection: "row", alignItems: "center", justifyContent: "space-between" }]}>
            <View style={{ flex: 1 }}>
              <Text style={styles.cardTitle}>
                {e.minuto != null ? `${e.minuto}'  ` : ""}{String(e.tipo).replace("_", " ")}
              </Text>
              <Text style={styles.cardSub}>
                {(e.jugador_nombre || "Sin jugador")} · {e.equipo_nombre || "—"}
              </Text>
            </View>
            {enJuego && (
              <TouchableOpacity onPress={() => borrarEvento(e.id)} style={live.del}>
                <Text style={{ color: colors.danger, fontWeight: "700" }}>✕</Text>
              </TouchableOpacity>
            )}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const live = {
  scoreRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  teamName: { color: colors.chalk, fontSize: 15, fontWeight: "700", flex: 1, textAlign: "center" },
  scoreBig: { color: colors.lime, fontSize: 40, fontWeight: "800", paddingHorizontal: 8 },
  seg: { flex: 1, borderColor: colors.line, borderWidth: 1, borderRadius: 10, paddingVertical: 12, alignItems: "center" },
  segText: { color: colors.chalk, fontWeight: "700" },
  chip: { borderColor: colors.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 9, marginRight: 8 },
  chipText: { color: colors.chalk, fontWeight: "600" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  evBtn: { width: "47%", borderRadius: 12, paddingVertical: 18, alignItems: "center" },
  evBtnText: { fontWeight: "800", fontSize: 16 },
  del: { padding: 10, marginLeft: 8 },
};
