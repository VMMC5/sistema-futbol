// Perfil del usuario autenticado: datos, cambio de contraseña y cerrar sesión.
import React from "react";
import { ScrollView, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../../auth";
import { cs, lp, ls } from "../../publicTheme";

export default function PerfilScreen({ navigation }) {
  const { usuario, logout } = useAuth();

  async function salir() {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: "Public" }] });
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      <View style={cs.featureGold}>
        <Text style={cs.featureGoldName}>{usuario?.nombre || "Usuario"}</Text>
        <Text style={cs.featureGoldMeta}>{usuario?.correo}</Text>
      </View>

      <View style={ls.infoRow}>
        <Text style={ls.infoLabel}>Rol</Text>
        <Text style={ls.infoValue}>{usuario?.rol}</Text>
      </View>

      <TouchableOpacity style={cs.ghostBtn} onPress={() => navigation.navigate("ChangePassword")}>
        <Text style={cs.ghostBtnText}>Cambiar contraseña</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[cs.ghostBtn, { marginTop: 10 }]} onPress={salir}>
        <Text style={[cs.ghostBtnText, { color: lp.danger }]}>Cerrar sesión</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
