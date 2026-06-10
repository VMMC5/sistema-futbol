// Pantalla de inicio de sesión.
import React, { useState } from "react";
import { Text, TextInput, TouchableOpacity, View, ScrollView } from "react-native";
import { useAuth, rutaPanel } from "../auth";
import { colors, styles } from "../theme";

export default function LoginScreen({ navigation }) {
  const { login } = useAuth();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function entrar() {
    setError("");
    setCargando(true);
    try {
      const { debeCambiar, usuario } = await login(correo.trim(), password);
      // Si el sistema exige cambio de contraseña (primer ingreso), va a esa pantalla.
      if (debeCambiar) {
        navigation.reset({ index: 0, routes: [{ name: "ChangePassword" }] });
      } else {
        navigation.reset({ index: 0, routes: [{ name: rutaPanel(usuario) }] });
      }
    } catch (e) {
      setError(e.message || "No se pudo iniciar sesión");
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Iniciar sesión</Text>
      <Text style={[styles.muted, { marginBottom: 24 }]}>Accede a tu panel</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Text style={styles.label}>Correo</Text>
      <TextInput
        style={styles.input}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="tucorreo@correo.com"
        placeholderTextColor={colors.muted}
        value={correo}
        onChangeText={setCorreo}
      />

      <Text style={styles.label}>Contraseña</Text>
      <TextInput
        style={styles.input}
        secureTextEntry
        placeholder="••••••••"
        placeholderTextColor={colors.muted}
        value={password}
        onChangeText={setPassword}
      />

      <TouchableOpacity style={styles.btn} onPress={entrar} disabled={cargando}>
        <Text style={styles.btnText}>{cargando ? "Entrando..." : "Entrar"}</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => navigation.navigate("RegisterPlayer")}>
        <Text style={styles.link}>Crear cuenta de jugador</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.navigate("RegisterStaff")}>
        <Text style={styles.link}>Soy entrenador o árbitro →</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
