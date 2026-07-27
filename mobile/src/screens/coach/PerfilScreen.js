// Perfil del usuario autenticado: datos, foto, cambio de contraseña y cerrar sesión.
import React, { useState } from "react";
import * as ImagePicker from "expo-image-picker";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import Avatar from "../../components/Avatar";
import { borrarFoto, subirFoto } from "../../api";
import { useAuth } from "../../auth";
import { cs, lp, ls } from "../../publicTheme";

export default function PerfilScreen({ navigation }) {
  const { usuario, logout, refrescar } = useAuth();
  const [subiendo, setSubiendo] = useState(false);
  const [fotoV, setFotoV] = useState(0);  // sube en cada cambio de foto -> refresca el Avatar

  async function salir() {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: "Public" }] });
  }

  async function cambiarFoto() {
    const permiso = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permiso.granted) {
      Alert.alert("Permiso necesario", "Habilita el acceso a tus fotos para cambiar la imagen de perfil.");
      return;
    }
    const resultado = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (resultado.canceled) return;
    setSubiendo(true);
    try {
      await subirFoto(resultado.assets[0].uri);
      await refrescar();
      setFotoV((v) => v + 1);
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo subir la foto");
    } finally {
      setSubiendo(false);
    }
  }

  function quitarFoto() {
    Alert.alert("Quitar foto", "¿Quitar tu foto de perfil?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Quitar",
        style: "destructive",
        onPress: async () => {
          setSubiendo(true);
          try {
            await borrarFoto();
            await refrescar();
            setFotoV((v) => v + 1);
          } catch (e) {
            Alert.alert("Error", e.message || "No se pudo quitar la foto");
          } finally {
            setSubiendo(false);
          }
        },
      },
    ]);
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      <View style={cs.featureGold}>
        <View style={{ alignItems: "center", marginBottom: 12 }}>
          <Avatar usuarioId={usuario?.id} nombre={usuario?.nombre} size={72} version={fotoV} />
        </View>
        <Text style={cs.featureGoldName}>{usuario?.nombre || "Usuario"}</Text>
        <Text style={cs.featureGoldMeta}>{usuario?.correo}</Text>
      </View>

      {subiendo && <ActivityIndicator color={lp.gold} style={{ marginBottom: 10 }} />}

      <TouchableOpacity style={cs.ghostBtn} onPress={cambiarFoto} disabled={subiendo}>
        <Text style={cs.ghostBtnText}>Cambiar foto</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[cs.ghostBtn, { marginTop: 10 }]} onPress={quitarFoto} disabled={subiendo}>
        <Text style={[cs.ghostBtnText, { color: lp.danger }]}>Quitar foto</Text>
      </TouchableOpacity>

      <View style={[ls.infoRow, { marginTop: 10 }]}>
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
