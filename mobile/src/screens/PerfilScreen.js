// PERFIL de entrenador y árbitro (ambos paneles montan esta pantalla).
// Misma estructura que la del jugador, sin cajas de estadísticas: no existe
// endpoint de stats agregadas para estos roles.
import React, { useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import Avatar from "../components/Avatar";
import EditarPerfilModal from "../components/EditarPerfilModal";
import OpcionMenu from "../components/OpcionMenu";
import useFotoPerfil from "../hooks/useFotoPerfil";
import { useAuth } from "../auth";
import { lp, ls } from "../publicTheme";

// El acento sigue a la cabecera de cada panel: dorada la del entrenador,
// guinda la del árbitro (ver goldHeader/maroonHeader en App.js).
const ACENTO = { entrenador: lp.gold, arbitro: lp.maroon };

export default function PerfilScreen({ navigation }) {
  const { usuario, logout } = useAuth();
  const [editar, setEditar] = useState(false);
  const [perfil, setPerfil] = useState(null);
  const { subiendo, fotoV, cambiarFoto, quitarFoto } = useFotoPerfil();

  const acento = ACENTO[usuario?.rol] || lp.accent;
  const nombreMostrar = perfil?.nombre || usuario?.nombre || "Usuario";

  async function cerrarSesion() {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: "Public" }] });
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Encabezado */}
      <View style={{ alignItems: "center", marginVertical: 12 }}>
        <Avatar usuarioId={usuario?.id} nombre={nombreMostrar} size={72} version={fotoV} />
        <Text style={{ color: lp.textDark, fontSize: 20, fontWeight: "800", marginTop: 12 }}>{nombreMostrar}</Text>
        <Text style={[ls.badge, { backgroundColor: lp.surface, color: acento, borderWidth: 1, borderColor: lp.surfaceBorder, marginTop: 6 }]}>
          {(usuario?.rol || "").toUpperCase()}
        </Text>
        {/* El jugador no muestra el correo; aquí sí estaba antes y no se le quita. */}
        <Text style={{ color: lp.textMuted, fontSize: 13, marginTop: 6 }}>{perfil?.correo || usuario?.correo}</Text>
        {subiendo && <ActivityIndicator color={acento} style={{ marginTop: 10 }} />}
        <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
          <TouchableOpacity style={fotoBtn} onPress={cambiarFoto} disabled={subiendo}>
            <Text style={[fotoBtnTxt, { color: acento }]}>Cambiar foto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[fotoBtn, { borderColor: lp.danger }]} onPress={quitarFoto} disabled={subiendo}>
            <Text style={[fotoBtnTxt, { color: lp.danger }]}>Quitar foto</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Accesos */}
      <OpcionMenu icono="edit" texto="Editar datos personales" onPress={() => setEditar(true)} />
      <OpcionMenu icono="creditcard" texto="Métodos de pago" onPress={() => Alert.alert("Métodos de pago", "Disponible próximamente.")} />
      <OpcionMenu icono="lock" texto="Cambiar contraseña" onPress={() => navigation.navigate("ChangePassword")} />
      <OpcionMenu icono="logout" texto="Cerrar sesión" color={lp.danger} onPress={cerrarSesion} />

      {/* Montaje condicional: ver la nota en EditarPerfilModal. */}
      {editar && (
        <EditarPerfilModal
          visible
          nombreInicial={perfil?.nombre || usuario?.nombre || ""}
          telefonoInicial={perfil?.telefono || usuario?.telefono || ""}
          acento={acento}
          onCerrar={() => setEditar(false)}
          onGuardado={(actualizado) => setPerfil(actualizado)}
        />
      )}
    </ScrollView>
  );
}

const fotoBtn = { borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 14 };
const fotoBtnTxt = { fontWeight: "700", fontSize: 13 };
