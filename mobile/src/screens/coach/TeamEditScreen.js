// Crear / editar equipo y su plantilla.
import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost, apiPut, apiDelete } from "../../api";
import { cs, lp, ls } from "../../publicTheme";

export default function TeamEditScreen({ route, navigation }) {
  const equipoId = route.params?.equipoId;
  const esNuevo = !equipoId;

  const [nombre, setNombre] = useState("");
  const [color, setColor] = useState("");
  const [categoria, setCategoria] = useState("");
  const [jugadores, setJugadores] = useState([]); // {nombre, posicion, dorsal}
  const [nuevo, setNuevo] = useState({ nombre: "", posicion: "", dorsal: "" });
  const [cargando, setCargando] = useState(!esNuevo);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    navigation.setOptions({ title: esNuevo ? "NUEVO EQUIPO" : "EDITAR EQUIPO" });
    if (esNuevo) return;
    (async () => {
      try {
        const e = await apiGet(`/equipos/${equipoId}`);
        setNombre(e.nombre || "");
        setColor(e.color || "");
        setCategoria(e.categoria || "");
        setJugadores((e.jugadores || []).map((j) => ({
          nombre: j.nombre || "", posicion: j.posicion || "", dorsal: j.dorsal != null ? String(j.dorsal) : "",
        })));
      } catch (e) {
        Alert.alert("Error", e.message || "No se pudo cargar el equipo");
      } finally {
        setCargando(false);
      }
    })();
  }, [equipoId]);

  function agregarJugador() {
    if (!nuevo.nombre.trim()) {
      Alert.alert("Falta el nombre", "Escribe el nombre del jugador.");
      return;
    }
    setJugadores([...jugadores, { ...nuevo, nombre: nuevo.nombre.trim() }]);
    setNuevo({ nombre: "", posicion: "", dorsal: "" });
  }

  function quitarJugador(idx) {
    setJugadores(jugadores.filter((_, i) => i !== idx));
  }

  async function guardar() {
    if (nombre.trim().length < 2) {
      Alert.alert("Falta el nombre", "El equipo necesita un nombre.");
      return;
    }
    setGuardando(true);
    const cuerpo = {
      nombre: nombre.trim(),
      color: color.trim() || null,
      categoria: categoria.trim() || null,
      jugadores: jugadores.map((j) => ({
        nombre: j.nombre,
        posicion: j.posicion?.trim() || null,
        dorsal: j.dorsal !== "" && !isNaN(parseInt(j.dorsal, 10)) ? parseInt(j.dorsal, 10) : null,
      })),
    };
    try {
      if (esNuevo) await apiPost("/equipos", cuerpo);
      else await apiPut(`/equipos/${equipoId}`, cuerpo);
      navigation.goBack();
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  function eliminarEquipo() {
    Alert.alert("Eliminar equipo", "¿Seguro que quieres eliminar este equipo?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Eliminar", style: "destructive",
        onPress: async () => {
          try {
            await apiDelete(`/equipos/${equipoId}`);
            navigation.goBack();
          } catch (e) {
            Alert.alert("No se pudo eliminar", e.message || "Intenta de nuevo");
          }
        },
      },
    ]);
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      <View style={cs.field}>
        <TextInput style={cs.input} placeholder="Nombre del equipo" placeholderTextColor={lp.textMuted} value={nombre} onChangeText={setNombre} />
      </View>
      <View style={cs.field}>
        <TextInput style={cs.input} placeholder="Color / uniforme" placeholderTextColor={lp.textMuted} value={color} onChangeText={setColor} />
      </View>
      <View style={cs.field}>
        <TextInput style={cs.input} placeholder="Categoría (Ej. Liga A, Sub-17)" placeholderTextColor={lp.textMuted} value={categoria} onChangeText={setCategoria} />
      </View>

      <Text style={ls.sectionTitle}>Plantilla de jugadores</Text>

      {jugadores.map((j, idx) => (
        <View key={idx} style={ls.row}>
          <View style={{ flex: 1 }}>
            <Text style={ls.rowTitle}>{j.nombre}</Text>
            <Text style={ls.rowSub}>
              {[j.posicion, j.dorsal !== "" ? `#${j.dorsal}` : null].filter(Boolean).join(" · ") || "Sin datos"}
            </Text>
          </View>
          <TouchableOpacity onPress={() => quitarJugador(idx)} style={{ padding: 8 }}>
            <Text style={{ color: lp.danger, fontWeight: "800", fontSize: 16 }}>✕</Text>
          </TouchableOpacity>
        </View>
      ))}

      {/* Mini-formulario para agregar jugador */}
      <View style={cs.playerForm}>
        <TextInput style={[cs.smallInput, { flex: 2 }]} placeholder="Nombre" placeholderTextColor={lp.textMuted}
          value={nuevo.nombre} onChangeText={(v) => setNuevo({ ...nuevo, nombre: v })} />
        <TextInput style={[cs.smallInput, { flex: 2 }]} placeholder="Posición" placeholderTextColor={lp.textMuted}
          value={nuevo.posicion} onChangeText={(v) => setNuevo({ ...nuevo, posicion: v })} />
        <TextInput style={[cs.smallInput, { width: 56 }]} placeholder="#" keyboardType="number-pad" placeholderTextColor={lp.textMuted}
          value={nuevo.dorsal} onChangeText={(v) => setNuevo({ ...nuevo, dorsal: v })} />
      </View>
      <TouchableOpacity style={cs.ghostBtn} onPress={agregarJugador}>
        <Text style={cs.ghostBtnText}>+ Agregar jugador</Text>
      </TouchableOpacity>

      <TouchableOpacity style={cs.primaryBtn} onPress={guardar} disabled={guardando}>
        <Text style={cs.primaryBtnText}>{guardando ? "Guardando..." : "Guardar equipo"}</Text>
      </TouchableOpacity>

      {!esNuevo && (
        <TouchableOpacity style={[cs.ghostBtn, { marginTop: 20 }]} onPress={eliminarEquipo}>
          <Text style={[cs.ghostBtnText, { color: lp.danger }]}>Eliminar equipo</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}
