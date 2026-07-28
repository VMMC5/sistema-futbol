// Subir y quitar la foto de perfil. Devuelve fotoV, que sube en cada cambio
// para que <Avatar version={fotoV}> descarte su caché (fix del PR #20).
import { useState } from "react";
import { Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { borrarFoto, subirFoto } from "../api";
import { useAuth } from "../auth";

export default function useFotoPerfil() {
  const { refrescar } = useAuth();
  const [subiendo, setSubiendo] = useState(false);
  const [fotoV, setFotoV] = useState(0);

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

  return { subiendo, fotoV, cambiarFoto, quitarFoto };
}
