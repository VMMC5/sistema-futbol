// Cambio de contraseña OBLIGATORIO en el primer ingreso (entrenadores/árbitros
// que entraron con la contraseña temporal del correo).
import React, { useState } from "react";
import { ScrollView, Text, TextInput, TouchableOpacity } from "react-native";
import { apiPost } from "../api";
import { useAuth, rutaPanel } from "../auth";
import { colors, styles } from "../theme";

export default function ChangePasswordScreen({ navigation }) {
  const { refrescar } = useAuth();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirma, setConfirma] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function cambiar() {
    setError("");
    if (nueva.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (nueva !== confirma) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setCargando(true);
    try {
      await apiPost("/auth/cambiar-password", {
        password_actual: actual,
        password_nueva: nueva,
      });
      const me = await refrescar();
      navigation.reset({ index: 0, routes: [{ name: rutaPanel(me) }] });
    } catch (e) {
      setError(e.message || "No se pudo cambiar la contraseña");
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Cambia tu contraseña</Text>
      <Text style={[styles.muted, { marginBottom: 24 }]}>
        Por seguridad, debes reemplazar la contraseña temporal antes de continuar.
      </Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Text style={styles.label}>Contraseña temporal (la del correo)</Text>
      <TextInput style={styles.input} secureTextEntry placeholderTextColor={colors.muted}
        value={actual} onChangeText={setActual} />

      <Text style={styles.label}>Nueva contraseña</Text>
      <TextInput style={styles.input} secureTextEntry placeholderTextColor={colors.muted}
        value={nueva} onChangeText={setNueva} />

      <Text style={styles.label}>Confirmar nueva contraseña</Text>
      <TextInput style={styles.input} secureTextEntry placeholderTextColor={colors.muted}
        value={confirma} onChangeText={setConfirma} />

      <TouchableOpacity style={styles.btn} onPress={cambiar} disabled={cargando}>
        <Text style={styles.btnText}>{cargando ? "Guardando..." : "Guardar y continuar"}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
