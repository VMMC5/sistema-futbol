// Comprobante de pago + descarga del PDF. Estilos autocontenidos.
import React, { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, Alert, StyleSheet } from "react-native";
import * as Sharing from "expo-sharing";
import { apiGet, descargarReciboPDF } from "../api";

export default function ComprobanteScreen({ route }) {
  const { pagoId } = route.params;
  const [pago, setPago] = useState(null);

  useEffect(() => {
    apiGet(`/pagos/${pagoId}`).then(setPago).catch((e) => Alert.alert("Error", e.message));
  }, [pagoId]);

  async function descargar() {
    try {
      const uri = await descargarReciboPDF(pagoId);
      if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(uri);
    } catch (e) {
      Alert.alert("No se pudo generar el recibo", e.message);
    }
  }

  if (!pago) return <ActivityIndicator style={{ marginTop: 40 }} />;

  const fila = (k, v) => (
    <View style={s.fila}>
      <Text style={s.k}>{k}</Text>
      <Text style={s.v}>{v}</Text>
    </View>
  );

  return (
    <View style={s.screen}>
      <Text style={s.title}>Comprobante</Text>
      {fila("Folio", pago.referencia || "-")}
      {fila("Concepto", pago.concepto || "-")}
      {fila("Monto", `$ ${Number(pago.monto).toFixed(2)}`)}
      {fila("Método", pago.metodo)}
      {fila("Estado", pago.estado)}
      {pago.estado === "completado" && (
        <TouchableOpacity style={s.btn} onPress={descargar}>
          <Text style={s.btnTxt}>Descargar PDF</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f4f6f5", padding: 20 },
  title: { fontSize: 24, fontWeight: "800", color: "#0f2c1b", marginBottom: 12 },
  fila: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8, borderBottomColor: "#e2e8e4", borderBottomWidth: 1 },
  k: { fontWeight: "700", color: "#0f2c1b" },
  v: { color: "#4b5f54" },
  btn: { backgroundColor: "#1f7a44", borderRadius: 10, paddingVertical: 15, alignItems: "center", marginTop: 20 },
  btnTxt: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
