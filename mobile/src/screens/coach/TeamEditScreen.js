// Crear / editar equipo. La plantilla se construye por INVITACIONES (no se teclea):
// aquí se ven los miembros (editar dorsal/posición o quitar) y se invita a jugadores.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, Modal, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost, apiPut, apiDelete } from "../../api";
import { cs, lp, ls } from "../../publicTheme";

export default function TeamEditScreen({ route, navigation }) {
  const equipoId = route.params?.equipoId;
  const esNuevo = !equipoId;

  const [nombre, setNombre] = useState("");
  const [color, setColor] = useState("");
  const [categoria, setCategoria] = useState("");
  const [jugadores, setJugadores] = useState([]);
  const [cargando, setCargando] = useState(!esNuevo);
  const [guardando, setGuardando] = useState(false);
  const [editando, setEditando] = useState(null); // miembro en edición (modal)
  const [edPos, setEdPos] = useState("");
  const [edDorsal, setEdDorsal] = useState("");

  const cargar = useCallback(async () => {
    if (esNuevo) return;
    try {
      const e = await apiGet(`/equipos/${equipoId}`);
      setNombre(e.nombre || ""); setColor(e.color || ""); setCategoria(e.categoria || "");
      setJugadores(e.jugadores || []);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar el equipo");
    } finally {
      setCargando(false);
    }
  }, [equipoId, esNuevo]);

  useFocusEffect(useCallback(() => {
    navigation.setOptions({ title: esNuevo ? "NUEVO EQUIPO" : "EDITAR EQUIPO" });
    cargar();
  }, [cargar]));

  async function guardar() {
    if (nombre.trim().length < 2) { Alert.alert("Falta el nombre", "El equipo necesita un nombre."); return; }
    setGuardando(true);
    const cuerpo = { nombre: nombre.trim(), color: color.trim() || null, categoria: categoria.trim() || null };
    try {
      if (esNuevo) {
        const nuevo = await apiPost("/equipos", cuerpo);
        // Pasa a modo edición para poder invitar jugadores
        navigation.replace("TeamEdit", { equipoId: nuevo.id });
      } else {
        await apiPut(`/equipos/${equipoId}`, cuerpo);
        Alert.alert("Listo", "Equipo guardado.");
      }
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  function quitarMiembro(je) {
    Alert.alert("Quitar jugador", `¿Quitar a ${je.nombre} del equipo?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Quitar", style: "destructive", onPress: async () => {
        try { const eq = await apiDelete(`/equipos/${equipoId}/jugadores/${je.id}`); setJugadores(eq.jugadores || []); }
        catch (e) { Alert.alert("Error", e.message); }
      }},
    ]);
  }

  function abrirEdicion(je) {
    setEditando(je); setEdPos(je.posicion || ""); setEdDorsal(je.dorsal != null ? String(je.dorsal) : "");
  }
  async function guardarEdicion() {
    try {
      const eq = await apiPut(`/equipos/${equipoId}/jugadores/${editando.id}`, {
        posicion: edPos.trim() || null,
        dorsal: edDorsal !== "" && !isNaN(parseInt(edDorsal, 10)) ? parseInt(edDorsal, 10) : null,
      });
      setJugadores(eq.jugadores || []); setEditando(null);
    } catch (e) { Alert.alert("Error", e.message); }
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      <View style={cs.field}><TextInput style={cs.input} placeholder="Nombre del equipo" placeholderTextColor={lp.textMuted} value={nombre} onChangeText={setNombre} /></View>
      <View style={cs.field}><TextInput style={cs.input} placeholder="Color / uniforme" placeholderTextColor={lp.textMuted} value={color} onChangeText={setColor} /></View>
      <View style={cs.field}><TextInput style={cs.input} placeholder="Categoría (Ej. Liga A, Sub-17)" placeholderTextColor={lp.textMuted} value={categoria} onChangeText={setCategoria} /></View>

      <TouchableOpacity style={cs.primaryBtn} onPress={guardar} disabled={guardando}>
        <Text style={cs.primaryBtnText}>{guardando ? "Guardando..." : "Guardar equipo"}</Text>
      </TouchableOpacity>

      {esNuevo ? (
        <Text style={[ls.muted, { marginTop: 16, textAlign: "center" }]}>
          Guarda el equipo para poder invitar jugadores.
        </Text>
      ) : (
        <>
          <Text style={[ls.sectionTitle, { marginTop: 22 }]}>Plantilla ({jugadores.length})</Text>
          {jugadores.length === 0 ? (
            <Text style={[ls.muted, { marginBottom: 10 }]}>Aún no hay jugadores. Invita a jugadores registrados.</Text>
          ) : (
            jugadores.map((j) => (
              <View key={j.id} style={ls.row}>
                <TouchableOpacity style={{ flex: 1 }} onPress={() => abrirEdicion(j)}>
                  <Text style={ls.rowTitle}>{j.nombre}</Text>
                  <Text style={ls.rowSub}>
                    {[j.posicion, j.dorsal != null ? `#${j.dorsal}` : null].filter(Boolean).join(" · ") || "Toca para asignar dorsal/posición"}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => quitarMiembro(j)} style={{ padding: 8 }}>
                  <Text style={{ color: lp.danger, fontWeight: "800", fontSize: 16 }}>✕</Text>
                </TouchableOpacity>
              </View>
            ))
          )}

          <TouchableOpacity style={cs.primaryBtn} onPress={() => navigation.navigate("InvitePlayers", { equipoId })}>
            <Text style={cs.primaryBtnText}>+ Invitar jugadores</Text>
          </TouchableOpacity>
        </>
      )}

      {/* Modal de edición de dorsal/posición */}
      <Modal visible={editando != null} transparent animationType="fade" onRequestClose={() => setEditando(null)}>
        <View style={modal.fondo}>
          <View style={modal.panel}>
            <Text style={modal.titulo}>{editando?.nombre}</Text>
            <Text style={[ls.muted, { fontWeight: "700", marginBottom: 6 }]}>Posición</Text>
            <TextInput style={cs.input} placeholder="Ej. Delantero" placeholderTextColor={lp.textMuted} value={edPos} onChangeText={setEdPos} />
            <Text style={[ls.muted, { fontWeight: "700", marginBottom: 6, marginTop: 10 }]}>Dorsal</Text>
            <TextInput style={cs.input} placeholder="Ej. 9" keyboardType="number-pad" placeholderTextColor={lp.textMuted} value={edDorsal} onChangeText={setEdDorsal} />
            <TouchableOpacity style={[cs.primaryBtn, { marginTop: 14 }]} onPress={guardarEdicion}>
              <Text style={cs.primaryBtnText}>Guardar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={cs.ghostBtn} onPress={() => setEditando(null)}>
              <Text style={cs.ghostBtnText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const modal = {
  fondo: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "center", padding: 24 },
  panel: { backgroundColor: lp.bg, borderRadius: 16, padding: 20 },
  titulo: { color: lp.textDark, fontWeight: "800", fontSize: 17, marginBottom: 14 },
};
