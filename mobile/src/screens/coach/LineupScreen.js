// Definir alineación: elige formación y coloca a los jugadores de la plantilla
// sobre la cancha. Guarda el plan en el backend.
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator, Alert, Modal, ScrollView, Text, TouchableOpacity, View,
} from "react-native";
import { apiGet, apiPut } from "../../api";
import { lp, ls } from "../../publicTheme";

// Cada formación se describe por líneas, de la defensa al ataque.
const FORMACIONES = {
  "4-4-2": [["POR"], ["DEF", "DEF", "DEF", "DEF"], ["MED", "MED", "MED", "MED"], ["DEL", "DEL"]],
  "4-3-3": [["POR"], ["DEF", "DEF", "DEF", "DEF"], ["MED", "MED", "MED"], ["DEL", "DEL", "DEL"]],
  "3-5-2": [["POR"], ["DEF", "DEF", "DEF"], ["MED", "MED", "MED", "MED", "MED"], ["DEL", "DEL"]],
};

// Convierte la formación en huecos con coordenadas (x,y en fracción 0..1).
function huecos(formacion) {
  const lineas = FORMACIONES[formacion];
  const slots = [];
  let orden = 0;
  const n = lineas.length;
  lineas.forEach((linea, r) => {
    // r=0 (POR) abajo; última línea (DEL) arriba
    const y = 0.9 - (r * 0.78) / (n - 1);
    linea.forEach((label, i) => {
      const x = (i + 1) / (linea.length + 1);
      slots.push({ orden, x, y, label });
      orden += 1;
    });
  });
  return slots;
}

export default function LineupScreen({ route, navigation }) {
  const { partidoId, equipoId, rival } = route.params;
  const [formacion, setFormacion] = useState("4-4-2");
  const [plantilla, setPlantilla] = useState([]);     // jugadores del equipo
  const [asignados, setAsignados] = useState({});     // { orden: jugador }
  const [slotActivo, setSlotActivo] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);

  const slots = useMemo(() => huecos(formacion), [formacion]);

  useEffect(() => {
    navigation.setOptions({ title: `ALINEACIÓN · VS ${(rival || "").toUpperCase()}` });
    (async () => {
      try {
        const [eq, plan] = await Promise.all([
          apiGet(`/equipos/${equipoId}`),
          apiGet(`/partidos/${partidoId}/plan?equipo_id=${equipoId}`),
        ]);
        setPlantilla(eq.jugadores || []);
        if (plan.formacion) setFormacion(plan.formacion);
        // Reconstruir asignaciones por 'orden'
        if (plan.jugadores?.length) {
          const porId = Object.fromEntries((eq.jugadores || []).map((j) => [j.id, j]));
          const mapa = {};
          plan.jugadores.forEach((j) => {
            const jug = porId[j.jugador_equipo_id];
            if (jug) mapa[j.orden] = jug;
          });
          setAsignados(mapa);
        }
      } catch (e) {
        Alert.alert("Error", e.message || "No se pudo cargar");
      } finally {
        setCargando(false);
      }
    })();
  }, [partidoId, equipoId]);

  // Al cambiar de formación, recoloca a los ya asignados en los nuevos huecos.
  function cambiarFormacion(f) {
    const previos = Object.keys(asignados).sort((a, b) => a - b).map((k) => asignados[k]);
    const nuevos = huecos(f);
    const mapa = {};
    previos.slice(0, nuevos.length).forEach((jug, i) => { mapa[nuevos[i].orden] = jug; });
    setFormacion(f);
    setAsignados(mapa);
  }

  const idsAsignados = new Set(Object.values(asignados).map((j) => j.id));
  const disponibles = plantilla.filter((j) => !idsAsignados.has(j.id));

  function elegir(jugador) {
    setAsignados({ ...asignados, [slotActivo.orden]: jugador });
    setSlotActivo(null);
  }
  function quitar() {
    const copia = { ...asignados };
    delete copia[slotActivo.orden];
    setAsignados(copia);
    setSlotActivo(null);
  }

  async function confirmar() {
    setGuardando(true);
    const jugadores = slots
      .filter((s) => asignados[s.orden])
      .map((s) => ({ jugador_equipo_id: asignados[s.orden].id, posicion: s.label, orden: s.orden }));
    try {
      await apiPut(`/partidos/${partidoId}/plan`, { equipo_id: equipoId, formacion, jugadores });
      Alert.alert("Listo", "Alineación guardada.", [{ text: "OK", onPress: () => navigation.goBack() }]);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Selector de formación */}
      <View style={ls.tabs}>
        {Object.keys(FORMACIONES).map((f) => (
          <TouchableOpacity key={f} style={[ls.tab, formacion === f && ls.tabActive]} onPress={() => cambiarFormacion(f)}>
            <Text style={[ls.tabText, formacion === f && ls.tabTextActive]}>{f}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Cancha */}
      <View style={cancha.campo}>
        <View style={cancha.lineaMedia} />
        <View style={cancha.circuloCentral} />
        {slots.map((s) => {
          const jug = asignados[s.orden];
          return (
            <TouchableOpacity
              key={s.orden}
              style={[
                cancha.slot,
                { left: `${s.x * 100}%`, top: `${s.y * 100}%` },
                jug ? cancha.slotLleno : cancha.slotVacio,
              ]}
              onPress={() => setSlotActivo(s)}
            >
              <Text style={jug ? cancha.slotTextoLleno : cancha.slotTextoVacio}>
                {jug ? (jug.dorsal != null ? jug.dorsal : (jug.nombre || "?").charAt(0)) : "+"}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <Text style={[ls.muted, { textAlign: "center", marginVertical: 10 }]}>
        {Object.keys(asignados).length} de {slots.length} posiciones asignadas
      </Text>

      <TouchableOpacity
        style={[ls.tab, { backgroundColor: lp.gold, paddingVertical: 15, borderRadius: 12 }]}
        onPress={confirmar}
        disabled={guardando}
      >
        <Text style={{ color: lp.goldText, fontWeight: "800", fontSize: 15 }}>
          {guardando ? "Guardando..." : "Confirmar alineación"}
        </Text>
      </TouchableOpacity>

      {/* Selector de jugador para el hueco tocado */}
      <Modal visible={slotActivo != null} transparent animationType="slide" onRequestClose={() => setSlotActivo(null)}>
        <TouchableOpacity style={hoja.fondo} activeOpacity={1} onPress={() => setSlotActivo(null)}>
          <View style={hoja.panel}>
            <Text style={hoja.titulo}>
              {slotActivo?.label} — elige jugador
            </Text>
            {slotActivo && asignados[slotActivo.orden] && (
              <TouchableOpacity style={hoja.item} onPress={quitar}>
                <Text style={{ color: lp.danger, fontWeight: "700" }}>Quitar de esta posición</Text>
              </TouchableOpacity>
            )}
            <ScrollView style={{ maxHeight: 320 }}>
              {disponibles.length === 0 ? (
                <Text style={[ls.muted, { padding: 14 }]}>No quedan jugadores disponibles. Agrega más a tu plantilla.</Text>
              ) : (
                disponibles.map((j) => (
                  <TouchableOpacity key={j.id} style={hoja.item} onPress={() => elegir(j)}>
                    <Text style={ls.rowTitle}>
                      {j.dorsal != null ? `#${j.dorsal}  ` : ""}{j.nombre}
                    </Text>
                    {j.posicion ? <Text style={ls.rowSub}>{j.posicion}</Text> : null}
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
    </ScrollView>
  );
}

const cancha = {
  campo: {
    width: "100%", aspectRatio: 0.66, backgroundColor: "#1C6B3A", borderRadius: 14,
    borderWidth: 2, borderColor: "rgba(255,255,255,0.35)", position: "relative", overflow: "hidden",
  },
  lineaMedia: { position: "absolute", top: "50%", left: 0, right: 0, height: 2, backgroundColor: "rgba(255,255,255,0.35)" },
  circuloCentral: {
    position: "absolute", top: "50%", left: "50%", width: 70, height: 70, borderRadius: 35,
    borderWidth: 2, borderColor: "rgba(255,255,255,0.35)", transform: [{ translateX: -35 }, { translateY: -35 }],
  },
  slot: {
    position: "absolute", width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center",
    transform: [{ translateX: -18 }, { translateY: -18 }],
  },
  slotVacio: { borderWidth: 2, borderColor: "rgba(255,255,255,0.7)", borderStyle: "dashed", backgroundColor: "rgba(0,0,0,0.15)" },
  slotLleno: { backgroundColor: "#FBFAF6" },
  slotTextoVacio: { color: "#fff", fontWeight: "800", fontSize: 16 },
  slotTextoLleno: { color: "#123D2A", fontWeight: "800", fontSize: 14 },
};

const hoja = {
  fondo: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "flex-end" },
  panel: { backgroundColor: lp.bg, borderTopLeftRadius: 18, borderTopRightRadius: 18, padding: 16, paddingBottom: 28 },
  titulo: { color: lp.textDark, fontWeight: "800", fontSize: 15, marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  item: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: lp.surfaceBorder },
};
