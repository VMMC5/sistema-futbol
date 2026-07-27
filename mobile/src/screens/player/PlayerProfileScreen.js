// MI PERFIL: avatar (foto o iniciales), datos, cajas de stats y accesos a
// editar datos personales, métodos de pago (próximamente), contraseña y
// cerrar sesión.
import React, { useCallback, useState } from "react";
import { useFocusEffect, CommonActions } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import Avatar from "../../components/Avatar";
import EditarPerfilModal from "../../components/EditarPerfilModal";
import OpcionMenu from "../../components/OpcionMenu";
import useFotoPerfil from "../../hooks/useFotoPerfil";
import { apiGet } from "../../api";
import { useAuth } from "../../auth";
import { lp, ls } from "../../publicTheme";

export default function PlayerProfileScreen({ navigation }) {
  const { usuario, logout } = useAuth();
  const [stats, setStats] = useState({ goles: 0, partidos: 0 });
  const [me, setMe] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [editar, setEditar] = useState(false);
  const { subiendo, fotoV, cambiarFoto, quitarFoto } = useFotoPerfil();

  const cargar = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([apiGet("/auth/me"), apiGet("/jugador/estadisticas")]);
      setMe(m); setStats(s);
    } catch (_) {} finally { setCargando(false); }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

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
        <Avatar usuarioId={me?.id || usuario?.id} nombre={nombreMostrar} size={72} version={fotoV} />
        <Text style={{ color: lp.textDark, fontSize: 20, fontWeight: "800", marginTop: 12 }}>{nombreMostrar}</Text>
        <Text style={[ls.badge, { backgroundColor: lp.surface, color: lp.green, borderWidth: 1, borderColor: lp.surfaceBorder, marginTop: 6 }]}>JUGADOR</Text>
        {subiendo && <ActivityIndicator color={lp.green} style={{ marginTop: 10 }} />}
        <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
          <TouchableOpacity style={fotoBtn} onPress={cambiarFoto} disabled={subiendo}>
            <Text style={fotoBtnTxt}>Cambiar foto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[fotoBtn, { borderColor: lp.danger }]} onPress={quitarFoto} disabled={subiendo}>
            <Text style={[fotoBtnTxt, { color: lp.danger }]}>Quitar foto</Text>
          </TouchableOpacity>
        </View>
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
      <OpcionMenu icono="edit" texto="Editar datos personales" onPress={() => setEditar(true)} />
      <OpcionMenu icono="creditcard" texto="Métodos de pago" onPress={() => Alert.alert("Métodos de pago", "Disponible próximamente.")} />
      <OpcionMenu icono="lock" texto="Cambiar contraseña" onPress={() => navigation.navigate("ChangePassword")} />
      <OpcionMenu icono="logout" texto="Cerrar sesión" color={lp.danger} onPress={cerrarSesion} />

      {/* Montaje condicional: cada apertura arranca con los valores actuales
          sin necesitar un useEffect que pise lo que el usuario escribe. */}
      {editar && (
        <EditarPerfilModal
          visible
          nombreInicial={me?.nombre || ""}
          telefonoInicial={me?.telefono || ""}
          acento={lp.accent}
          onCerrar={() => setEditar(false)}
          onGuardado={(actualizado) => setMe(actualizado)}
        />
      )}
    </ScrollView>
  );
}

const fotoBtn = { borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 14 };
const fotoBtnTxt = { color: lp.green, fontWeight: "700", fontSize: 13 };
const box = { flex: 1, borderRadius: 14, paddingVertical: 18, alignItems: "center" };
const boxNum = { color: lp.white, fontSize: 26, fontWeight: "800" };
const boxLbl = { color: "rgba(255,255,255,0.9)", fontSize: 11, fontWeight: "700", letterSpacing: 1, marginTop: 2 };
