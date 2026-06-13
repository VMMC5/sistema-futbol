// NOTIFICACIONES (Avisos): invitaciones a equipo con aceptar/rechazar y avisos
// con opción de eliminar. Al abrir, marca los avisos como leídos.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost, apiDelete } from "../../api";
import { lp, ls } from "../../publicTheme";

const ICONO = (titulo = "") => {
  const t = titulo.toLowerCase();
  if (t.includes("gol")) return { e: "⚽", bg: lp.green };
  if (t.includes("pago")) return { e: "$", bg: "#E6C84F" };
  if (t.includes("torneo")) return { e: "🏆", bg: lp.green };
  if (t.includes("convocatoria")) return { e: "!", bg: lp.red };
  return { e: "🔔", bg: lp.accent };
};

export default function NotificationsScreen() {
  const [notis, setNotis] = useState([]);
  const [invitaciones, setInvitaciones] = useState([]);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      const [n, inv] = await Promise.all([apiGet("/notificaciones"), apiGet("/invitaciones/mias")]);
      setNotis(n);
      setInvitaciones(inv);
      // Marca como leídas al abrir
      if (n.some((x) => !x.leida)) apiPost("/notificaciones/marcar-leidas", {}).catch(() => {});
    } catch (_) {
      setNotis([]); setInvitaciones([]);
    } finally {
      setCargando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function responderInv(inv, accion) {
    try {
      await apiPost(`/invitaciones/${inv.id}/${accion}`, {});
      setInvitaciones((p) => p.filter((i) => i.id !== inv.id));
      if (accion === "aceptar") Alert.alert("¡Listo!", `Ahora eres parte de ${inv.equipo_nombre}.`);
    } catch (e) { Alert.alert("Error", e.message); cargar(); }
  }

  async function eliminar(n) {
    try { await apiDelete(`/notificaciones/${n.id}`); setNotis((p) => p.filter((x) => x.id !== n.id)); }
    catch (e) { Alert.alert("Error", e.message); }
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.green} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Invitaciones a equipo (accionables) */}
      {invitaciones.map((inv) => (
        <View key={`inv-${inv.id}`} style={[ls.row, { flexDirection: "column", alignItems: "stretch" }]}>
          <Text style={ls.rowTitle}>Invitación · {inv.equipo_nombre}</Text>
          <Text style={ls.rowSub}>{inv.entrenador_nombre ? `${inv.entrenador_nombre} te invitó a unirte.` : "Te invitaron a unirte."}</Text>
          <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
            <TouchableOpacity style={[accBtn, { backgroundColor: lp.accent, flex: 1 }]} onPress={() => responderInv(inv, "aceptar")}>
              <Text style={{ color: lp.white, fontWeight: "800" }}>Aceptar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[accBtn, { backgroundColor: lp.surface, borderWidth: 1, borderColor: lp.surfaceBorder, flex: 1 }]} onPress={() => responderInv(inv, "rechazar")}>
              <Text style={{ color: lp.danger, fontWeight: "800" }}>Rechazar</Text>
            </TouchableOpacity>
          </View>
        </View>
      ))}

      {/* Avisos */}
      {notis.length === 0 && invitaciones.length === 0 ? (
        <Text style={[ls.empty, { marginTop: 30 }]}>No tienes notificaciones.</Text>
      ) : (
        notis.map((n) => {
          const ic = ICONO(n.titulo);
          return (
            <View key={n.id} style={[ls.row, { alignItems: "center" }]}>
              <View style={[circ, { backgroundColor: ic.bg }]}>
                <Text style={{ color: lp.white, fontWeight: "800" }}>{ic.e}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={ls.rowTitle}>{n.titulo || "Aviso"}</Text>
                {!!n.mensaje && <Text style={ls.rowSub}>{n.mensaje}</Text>}
              </View>
              <TouchableOpacity onPress={() => eliminar(n)} style={{ padding: 8 }}>
                <Text style={{ color: lp.textMuted, fontSize: 16, fontWeight: "800" }}>✕</Text>
              </TouchableOpacity>
            </View>
          );
        })
      )}
    </ScrollView>
  );
}

const accBtn = { borderRadius: 10, paddingVertical: 11, alignItems: "center" };
const circ = { width: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center", marginRight: 12 };
