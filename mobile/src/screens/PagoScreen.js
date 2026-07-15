// Pantalla de pago reutilizable para reservas e inscripciones.
// Estilos autocontenidos (no depende de theme.js) para verse bien en el flujo claro.
import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert, ScrollView, StyleSheet,
} from "react-native";
import { apiPost } from "../api";
import { validarTarjeta } from "../validacion";

export default function PagoScreen({ route, navigation }) {
  const { tipo, id, resumen } = route.params; // tipo: "reserva" | "inscripcion"
  const [metodo, setMetodo] = useState("tarjeta");
  const [numero, setNumero] = useState("");
  const [expMes, setExpMes] = useState("");
  const [expAnio, setExpAnio] = useState("");
  const [cvv, setCvv] = useState("");
  const [titular, setTitular] = useState("");
  const [cargando, setCargando] = useState(false);

  async function pagar() {
    if (metodo === "tarjeta") {
      const problema = validarTarjeta({ numero, cvv, titular, expMes, expAnio });
      if (problema) {
        Alert.alert("Revisa los datos de la tarjeta", problema);
        return;
      }
    }
    setCargando(true);
    try {
      const body = { metodo };
      if (metodo === "tarjeta") {
        body.tarjeta = {
          numero, cvv, titular,
          exp_mes: parseInt(expMes, 10),
          exp_anio: parseInt(expAnio, 10),
        };
      }
      const pago = await apiPost(`/pagos/${tipo}/${id}`, body);
      navigation.replace("Comprobante", { pagoId: pago.id });
    } catch (e) {
      Alert.alert("Pago no procesado", e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      <Text style={s.title}>Pago</Text>
      {resumen ? <Text style={s.resumen}>{resumen}</Text> : null}

      <View style={s.tabs}>
        {["tarjeta", "transferencia"].map((m) => (
          <TouchableOpacity key={m} onPress={() => setMetodo(m)} style={[s.tab, metodo === m && s.tabOn]}>
            <Text style={[s.tabTxt, metodo === m && s.tabTxtOn]}>
              {m === "tarjeta" ? "Tarjeta" : "Transferencia"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {metodo === "tarjeta" && (
        <>
          <TextInput style={s.input} placeholder="Número de tarjeta" keyboardType="number-pad"
            value={numero} onChangeText={setNumero} />
          <View style={{ flexDirection: "row" }}>
            <TextInput style={[s.input, { flex: 1, marginRight: 6 }]} placeholder="MM"
              keyboardType="number-pad" value={expMes} onChangeText={setExpMes} />
            <TextInput style={[s.input, { flex: 1, marginHorizontal: 6 }]} placeholder="AAAA"
              keyboardType="number-pad" value={expAnio} onChangeText={setExpAnio} />
            <TextInput style={[s.input, { flex: 1, marginLeft: 6 }]} placeholder="CVV"
              keyboardType="number-pad" value={cvv} onChangeText={setCvv} />
          </View>
          <TextInput style={s.input} placeholder="Titular" value={titular} onChangeText={setTitular} />
        </>
      )}

      {metodo === "transferencia" && (
        <Text style={s.nota}>
          Se registrará tu pago por transferencia. Quedará pendiente hasta que un
          administrador lo confirme.
        </Text>
      )}

      <TouchableOpacity style={s.btn} onPress={pagar} disabled={cargando}>
        {cargando ? <ActivityIndicator color="#fff" /> : <Text style={s.btnTxt}>Pagar</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f4f6f5" },
  content: { padding: 20 },
  title: { fontSize: 24, fontWeight: "800", color: "#0f2c1b", marginBottom: 6 },
  resumen: { color: "#4b5f54", fontSize: 14, marginBottom: 8 },
  tabs: { flexDirection: "row", marginVertical: 12 },
  tab: { flex: 1, padding: 12, marginHorizontal: 4, borderRadius: 8, backgroundColor: "#e5e7eb" },
  tabOn: { backgroundColor: "#1f7a44" },
  tabTxt: { textAlign: "center", color: "#111", fontWeight: "700" },
  tabTxtOn: { color: "#fff" },
  input: {
    backgroundColor: "#fff", borderColor: "#d3dbd6", borderWidth: 1, borderRadius: 10,
    color: "#111", paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, marginBottom: 12,
  },
  nota: { color: "#4b5f54", fontSize: 14, marginBottom: 12 },
  btn: { backgroundColor: "#1f7a44", borderRadius: 10, paddingVertical: 15, alignItems: "center", marginTop: 6 },
  btnTxt: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
