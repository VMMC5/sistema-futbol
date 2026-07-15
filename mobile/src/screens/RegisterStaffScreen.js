// Solicitud de alta como ENTRENADOR / ÁRBITRO.
// Incluye la subida de un documento (PDF o imagen) que el administrador revisará.
import React, { useState } from "react";
import { ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { apiPostForm } from "../api";
import { validarSolicitudStaff } from "../validacion";
import { colors, styles } from "../theme";

export default function RegisterStaffScreen() {
  const [form, setForm] = useState({ nombre: "", correo: "", telefono: "" });
  const [rol, setRol] = useState("entrenador");
  const [archivo, setArchivo] = useState(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [cargando, setCargando] = useState(false);

  const set = (k) => (v) => setForm({ ...form, [k]: v });

  async function elegirDocumento() {
    const res = await DocumentPicker.getDocumentAsync({
      type: ["application/pdf", "image/png", "image/jpeg"],
      copyToCacheDirectory: true,
    });
    if (!res.canceled && res.assets && res.assets.length) {
      setArchivo(res.assets[0]); // { uri, name, mimeType, size }
    }
  }

  async function enviar() {
    setError("");
    setOk("");
    const problema = validarSolicitudStaff(form);
    if (problema) {
      setError(problema);
      return;
    }
    if (!archivo) {
      setError("Adjunta tu documento (PDF o imagen).");
      return;
    }
    setCargando(true);
    try {
      const fd = new FormData();
      fd.append("nombre", form.nombre.trim());
      fd.append("correo", form.correo.trim());
      fd.append("rol_solicitado", rol);
      if (form.telefono.trim()) fd.append("telefono", form.telefono.trim());
      fd.append("documento", {
        uri: archivo.uri,
        name: archivo.name || "documento",
        type: archivo.mimeType || "application/octet-stream",
      });

      await apiPostForm("/solicitudes", fd);
      setOk(
        "Solicitud enviada. El administrador revisará tu documento. " +
          "Si es aprobada, recibirás un correo con una contraseña temporal para tu primer ingreso."
      );
      setForm({ nombre: "", correo: "", telefono: "" });
      setArchivo(null);
    } catch (e) {
      setError(e.message || "No se pudo enviar la solicitud");
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Entrenador / Árbitro</Text>
      <Text style={[styles.muted, { marginBottom: 24 }]}>
        Solicita tu alta. Un administrador validará tu acreditación.
      </Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {ok ? <Text style={styles.ok}>{ok}</Text> : null}

      {/* Selector de rol */}
      <Text style={styles.label}>¿Cómo te registras?</Text>
      <View style={{ flexDirection: "row", gap: 10, marginBottom: 16 }}>
        {["entrenador", "arbitro"].map((opcion) => (
          <TouchableOpacity
            key={opcion}
            onPress={() => setRol(opcion)}
            style={[
              seg.item,
              rol === opcion && { backgroundColor: colors.lime, borderColor: colors.lime },
            ]}
          >
            <Text style={[seg.text, rol === opcion && { color: colors.pitch900 }]}>
              {opcion === "entrenador" ? "Entrenador" : "Árbitro"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

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

      <Text style={styles.label}>Documento de acreditación (PDF o imagen)</Text>
      <TouchableOpacity style={styles.btnGhost} onPress={elegirDocumento}>
        <Text style={styles.btnGhostText}>
          {archivo ? `📎 ${archivo.name}` : "Adjuntar documento"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity style={[styles.btn, { marginTop: 20 }]} onPress={enviar} disabled={cargando}>
        <Text style={styles.btnText}>{cargando ? "Enviando..." : "Enviar solicitud"}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const seg = {
  item: {
    flex: 1,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  text: { color: colors.chalk, fontWeight: "700" },
};
