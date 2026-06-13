// MI PERFIL: avatar con iniciales, datos, cajas de stats y accesos a editar
// datos personales, métodos de pago (próximamente), contraseña y cerrar sesión.
import React, { useCallback, useState } from "react";
import { useFocusEffect, CommonActions } from "@react-navigation/native";
import { ActivityIndicator, Alert, Modal, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiGet, apiPut } from "../../api";
import { useAuth } from "../../auth";
import { lp, ls } from "../../publicTheme";

function iniciales(nombre = "") {
  const p = nombre.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p[1]?.[0] || "")).toUpperCase() || "?";
}

export default function PlayerProfileScreen({ navigation }) {
  const { usuario, logout, refrescar } = useAuth();
  const [stats, setStats] = useState({ goles: 0, partidos: 0 });
  const [me, setMe] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [editar, setEditar] = useState(false);
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([apiGet("/auth/me"), apiGet("/jugador/estadisticas")]);
      setMe(m); setStats(s);
    } catch (_) {} finally { setCargando(false); }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  function abrirEdicion() {
    setNombre(me?.nombre || ""); setTelefono(me?.telefono || ""); setEditar(true);
  }

  async function guardar() {
    if (nombre.trim().length < 2) { Alert.alert("Nombre inválido", "Escribe tu nombre completo."); return; }
    setGuardando(true);
    try {
      const actualizado = await apiPut("/auth/me", { nombre: nombre.trim(), telefono: telefono.trim() });
      setMe(actualizado);
      await refrescar();
      setEditar(false);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  async function cerrarSesion() {
    await logout();
    navigation.dispatch(CommonActions.reset({ index: 0, routes: [{ name: "Public" }] }));
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.green} style={{ marginTop: 40 }} /></View>;
  }

  const nombreMostrar = me?.nombre || usuario?.nombre || "Jugador";

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Encabezado */}
      <View style={{ alignItems: "center", marginVertical: 12 }}>
        <View style={avatar.circ}><Text style={avatar.txt}>{iniciales(nombreMostrar)}</Text></View>
        <Text style={{ color: lp.textDark, fontSize: 20, fontWeight: "800", marginTop: 12 }}>{nombreMostrar}</Text>
        <Text style={[ls.badge, { backgroundColor: lp.surface, color: lp.green, borderWidth: 1, borderColor: lp.surfaceBorder, marginTop: 6 }]}>JUGADOR</Text>
      </View>

      {/* Stats */}
      <View style={{ flexDirection: "row", gap: 10, marginBottom: 18 }}>
        <View style={[box, { backgroundColor: lp.green }]}>
          <Text style={boxNum}>{stats.goles}</Text><Text style={boxLbl}>GOLES</Text>
        </View>
        <View style={[box, { backgroundColor: lp.accent }]}>
          <Text style={boxNum}>{stats.partidos}</Text><Text style={boxLbl}>PARTIDOS</Text>
        </View>
      </View>

      {/* Accesos */}
      <Opcion icono="✎" texto="Editar datos personales" onPress={abrirEdicion} />
      <Opcion icono="💳" texto="Métodos de pago" onPress={() => Alert.alert("Métodos de pago", "Disponible próximamente.")} />
      <Opcion icono="🔒" texto="Cambiar contraseña" onPress={() => navigation.navigate("ChangePassword")} />
      <Opcion icono="⊗" texto="Cerrar sesión" color={lp.danger} onPress={cerrarSesion} />

      {/* Modal editar */}
      <Modal visible={editar} transparent animationType="fade" onRequestClose={() => setEditar(false)}>
        <View style={modal.fondo}>
          <View style={modal.panel}>
            <Text style={modal.titulo}>Editar datos personales</Text>
            <Text style={campoLbl}>Nombre</Text>
            <TextInput style={input} value={nombre} onChangeText={setNombre} placeholder="Tu nombre" placeholderTextColor={lp.textMuted} />
            <Text style={[campoLbl, { marginTop: 10 }]}>Teléfono</Text>
            <TextInput style={input} value={telefono} onChangeText={setTelefono} keyboardType="phone-pad" placeholder="Opcional" placeholderTextColor={lp.textMuted} />
            <TouchableOpacity style={[guardarBtn, guardando && { opacity: 0.6 }]} onPress={guardar} disabled={guardando}>
              <Text style={{ color: lp.white, fontWeight: "800" }}>{guardando ? "Guardando..." : "Guardar"}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={{ paddingVertical: 12, alignItems: "center" }} onPress={() => setEditar(false)}>
              <Text style={{ color: lp.textMuted, fontWeight: "700" }}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

function Opcion({ icono, texto, onPress, color }) {
  return (
    <TouchableOpacity style={[ls.row, { alignItems: "center" }]} onPress={onPress}>
      <Text style={{ fontSize: 16, marginRight: 12 }}>{icono}</Text>
      <Text style={{ flex: 1, fontWeight: "700", color: color || lp.textDark }}>{texto}</Text>
      <Text style={{ color: lp.textMuted, fontSize: 20 }}>›</Text>
    </TouchableOpacity>
  );
}

const avatar = {
  circ: { width: 88, height: 88, borderRadius: 44, backgroundColor: lp.accent, alignItems: "center", justifyContent: "center" },
  txt: { color: lp.white, fontSize: 30, fontWeight: "800" },
};
const box = { flex: 1, borderRadius: 14, paddingVertical: 18, alignItems: "center" };
const boxNum = { color: lp.white, fontSize: 26, fontWeight: "800" };
const boxLbl = { color: "rgba(255,255,255,0.9)", fontSize: 11, fontWeight: "700", letterSpacing: 1, marginTop: 2 };
const modal = {
  fondo: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "center", padding: 24 },
  panel: { backgroundColor: lp.bg, borderRadius: 16, padding: 20 },
  titulo: { color: lp.textDark, fontWeight: "800", fontSize: 17, marginBottom: 14 },
};
const campoLbl = { color: lp.textMuted, fontWeight: "700", marginBottom: 6 };
const input = { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, color: lp.textDark, paddingHorizontal: 14, paddingVertical: 12 };
const guardarBtn = { backgroundColor: lp.accent, borderRadius: 10, paddingVertical: 14, alignItems: "center", marginTop: 16 };
