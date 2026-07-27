// Modal de "Editar datos personales" (nombre y teléfono) contra PUT /auth/me.
// Los valores iniciales llegan por props: useAuth().usuario ya trae ambos, así
// que el modal no pide nada al abrirse.
import React, { useEffect, useState } from "react";
import { Alert, Modal, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiPut } from "../api";
import { useAuth } from "../auth";
import { lp } from "../publicTheme";

export default function EditarPerfilModal({
  visible, nombreInicial, telefonoInicial, acento = lp.accent, onCerrar, onGuardado,
}) {
  const { refrescar } = useAuth();
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [guardando, setGuardando] = useState(false);

  // Al abrirse, parte siempre de los valores actuales.
  useEffect(() => {
    if (visible) {
      setNombre(nombreInicial || "");
      setTelefono(telefonoInicial || "");
    }
  }, [visible, nombreInicial, telefonoInicial]);

  async function guardar() {
    if (nombre.trim().length < 2) {
      Alert.alert("Nombre inválido", "Escribe tu nombre completo.");
      return;
    }
    setGuardando(true);
    try {
      const actualizado = await apiPut("/auth/me", { nombre: nombre.trim(), telefono: telefono.trim() });
      await refrescar();
      onGuardado?.(actualizado);
      onCerrar();
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCerrar}>
      <View style={estilos.fondo}>
        <View style={estilos.panel}>
          <Text style={estilos.titulo}>Editar datos personales</Text>
          <Text style={estilos.campoLbl}>Nombre</Text>
          <TextInput
            style={estilos.input} value={nombre} onChangeText={setNombre}
            placeholder="Tu nombre" placeholderTextColor={lp.textMuted}
          />
          <Text style={[estilos.campoLbl, { marginTop: 10 }]}>Teléfono</Text>
          <TextInput
            style={estilos.input} value={telefono} onChangeText={setTelefono}
            keyboardType="phone-pad" placeholder="Opcional" placeholderTextColor={lp.textMuted}
          />
          <TouchableOpacity
            style={[estilos.guardarBtn, { backgroundColor: acento }, guardando && { opacity: 0.6 }]}
            onPress={guardar} disabled={guardando}
          >
            <Text style={{ color: lp.white, fontWeight: "800" }}>{guardando ? "Guardando..." : "Guardar"}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={{ paddingVertical: 12, alignItems: "center" }} onPress={onCerrar}>
            <Text style={{ color: lp.textMuted, fontWeight: "700" }}>Cancelar</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const estilos = {
  fondo: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "center", padding: 24 },
  panel: { backgroundColor: lp.bg, borderRadius: 16, padding: 20 },
  titulo: { color: lp.textDark, fontWeight: "800", fontSize: 17, marginBottom: 14 },
  campoLbl: { color: lp.textMuted, fontWeight: "700", marginBottom: 6 },
  input: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, color: lp.textDark, paddingHorizontal: 14, paddingVertical: 12 },
  guardarBtn: { borderRadius: 10, paddingVertical: 14, alignItems: "center", marginTop: 16 },
};
