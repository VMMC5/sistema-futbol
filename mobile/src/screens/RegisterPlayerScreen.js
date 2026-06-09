// Registro de JUGADOR (auto-registro estándar).
import React, { useState } from "react";
import { ScrollView, Text, TextInput, TouchableOpacity } from "react-native";
import { apiPost } from "../api";
import { colors, styles } from "../theme";

export default function RegisterPlayerScreen({ navigation }) {
  const [form, setForm] = useState({ nombre: "", correo: "", password: "", telefono: "" });
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  const set = (k) => (v) => setForm({ ...form, [k]: v });

  async function registrar() {
    setError("");
    setCargando(true);
    try {
      await apiPost(
        "/auth/register",
        {
          nombre: form.nombre.trim(),
          correo: form.correo.trim(),
          password: form.password,
          telefono: form.telefono.trim() || null,
        },
        false
      );
      navigation.reset({ index: 1, routes: [{ name: "Landing" }, { name: "Login" }] });
    } catch (e) {
      setError(e.message || "No se pudo crear la cuenta");
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Crear cuenta</Text>
      <Text style={[styles.muted, { marginBottom: 24 }]}>Cuenta de jugador</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Text style={styles.label}>Nombre</Text>
      <TextInput style={styles.input} placeholder="Tu nombre" placeholderTextColor={colors.muted}
        value={form.nombre} onChangeText={set("nombre")} />

      <Text style={styles.label}>Correo</Text>
      <TextInput style={styles.input} autoCapitalize="none" keyboardType="email-address"
        placeholder="tucorreo@correo.com" placeholderTextColor={colors.muted}
        value={form.correo} onChangeText={set("correo")} />

      <Text style={styles.label}>Teléfono (opcional)</Text>
      <TextInput style={styles.input} keyboardType="phone-pad" placeholder="771 000 0000"
        placeholderTextColor={colors.muted} value={form.telefono} onChangeText={set("telefono")} />

      <Text style={styles.label}>Contraseña (mínimo 8 caracteres)</Text>
      <TextInput style={styles.input} secureTextEntry placeholder="••••••••"
        placeholderTextColor={colors.muted} value={form.password} onChangeText={set("password")} />

      <TouchableOpacity style={styles.btn} onPress={registrar} disabled={cargando}>
        <Text style={styles.btnText}>{cargando ? "Creando..." : "Crear cuenta"}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
