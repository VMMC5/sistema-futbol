// RESERVAR CANCHA: buscar sede, elegir una de sus canchas, fecha y horario
// (los horarios ocupados se deshabilitan). Sin pantallas de pago todavía.
import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { lp, ls } from "../../publicTheme";
import { useNavigation } from "@react-navigation/native";

const SLOTS = ["16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"];
const DIAS_CORTOS = ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"];

function proximosDias(n = 7) {
  const hoy = new Date();
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() + i);
    return {
      clave: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`,
      etiqueta: `${DIAS_CORTOS[d.getDay()]} ${d.getDate()}`,
    };
  });
}

export default function ReservarScreen() {
  const dias = proximosDias();
  const navigation = useNavigation();
  const [buscar, setBuscar] = useState("");
  const [sedes, setSedes] = useState([]);
  const [sedeSel, setSedeSel] = useState(null);
  const [canchas, setCanchas] = useState([]);
  const [canchaSel, setCanchaSel] = useState(null);
  const [fechaSel, setFechaSel] = useState(dias[0].clave);
  const [ocupados, setOcupados] = useState([]);
  const [horaSel, setHoraSel] = useState(null);
  const [guardando, setGuardando] = useState(false);

  // Buscar sedes (debounce)
  useEffect(() => {
    let activo = true;
    const t = setTimeout(async () => {
      try { const r = await apiGet(`/sedes?buscar=${encodeURIComponent(buscar.trim())}`); if (activo) setSedes(r); }
      catch (_) { if (activo) setSedes([]); }
    }, 300);
    return () => { activo = false; clearTimeout(t); };
  }, [buscar]);

  // Al elegir sede, cargar sus canchas
  async function elegirSede(s) {
    setSedeSel(s); setSedes([]); setBuscar(s.nombre); setCanchaSel(null); setHoraSel(null);
    try { setCanchas(await apiGet(`/canchas?sede_id=${s.id}`)); } catch (_) { setCanchas([]); }
  }

  // Disponibilidad al cambiar cancha o fecha
  useEffect(() => {
    if (!canchaSel) { setOcupados([]); return; }
    let activo = true;
    (async () => {
      try {
        const r = await apiGet(`/canchas/${canchaSel.id}/disponibilidad?fecha=${fechaSel}`);
        if (activo) { setOcupados(r.ocupados || []); setHoraSel(null); }
      } catch (_) { if (activo) setOcupados([]); }
    })();
    return () => { activo = false; };
  }, [canchaSel, fechaSel]);

  async function reservar() {
    if (!canchaSel || !horaSel) { Alert.alert("Faltan datos", "Elige cancha y horario."); return; }
    setGuardando(true);
    const finH = `${String(parseInt(horaSel, 10) + 1).padStart(2, "0")}:00`;
    try {
      const r = await apiPost("/reservas", { cancha_id: canchaSel.id, fecha: fechaSel, hora_inicio: horaSel, hora_fin: finH });
      setHoraSel(null);
      setOcupados((o) => [...o, horaSel]);
      navigation.navigate("Pago", {
        tipo: "reserva",
        id: r.id,
        resumen: `Reserva ${canchaSel.nombre} · ${fechaSel} · ${horaSel}`,
      });
    } catch (e) {
      Alert.alert("No se pudo reservar", e.message || "Intenta de nuevo");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content} keyboardShouldPersistTaps="handled">
      {/* Buscador de sede */}
      <View style={{ backgroundColor: lp.white, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 4, marginBottom: 8 }}>
        <TextInput
          style={{ color: lp.textDark, paddingVertical: 12, fontSize: 15 }}
          placeholder="📍 Buscar sede" placeholderTextColor={lp.textMuted}
          value={buscar} onChangeText={(t) => { setBuscar(t); setSedeSel(null); }}
        />
      </View>
      {sedes.length > 0 && !sedeSel && (
        <View style={{ marginBottom: 8 }}>
          {sedes.map((s) => (
            <TouchableOpacity key={s.id} style={ls.row} onPress={() => elegirSede(s)}>
              <View style={{ flex: 1 }}>
                <Text style={ls.rowTitle}>{s.nombre}</Text>
                {!!s.ciudad && <Text style={ls.rowSub}>{s.ciudad}</Text>}
              </View>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {sedeSel && (
        <>
          {/* Canchas de la sede */}
          <Text style={ls.sectionTitle}>Canchas</Text>
          {canchas.length === 0 ? (
            <Text style={ls.muted}>Esta sede no tiene canchas.</Text>
          ) : (
            canchas.map((c) => {
              const activo = canchaSel?.id === c.id;
              return (
                <TouchableOpacity key={c.id} style={[ls.row, activo && { borderColor: lp.green, borderWidth: 2 }]} onPress={() => setCanchaSel(c)}>
                  <View style={{ flex: 1 }}>
                    <Text style={ls.rowTitle}>{c.nombre}</Text>
                    <Text style={ls.rowSub}>{[c.tipo, c.disponible ? null : "no disponible"].filter(Boolean).join(" · ")}</Text>
                  </View>
                  <Text style={{ color: lp.green, fontWeight: "800" }}>{c.precio_hora != null ? `$${c.precio_hora}` : ""}</Text>
                </TouchableOpacity>
              );
            })
          )}

          {canchaSel && (
            <>
              {/* Fecha */}
              <Text style={[ls.sectionTitle, { marginTop: 14 }]}>Fecha</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 6 }}>
                {dias.map((d) => (
                  <TouchableOpacity key={d.clave} style={[diaChip.base, fechaSel === d.clave && diaChip.on]} onPress={() => setFechaSel(d.clave)}>
                    <Text style={[diaChip.txt, fechaSel === d.clave && diaChip.txtOn]}>{d.etiqueta}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {/* Horarios */}
              <Text style={[ls.sectionTitle, { marginTop: 10 }]}>Horarios disponibles</Text>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
                {SLOTS.map((h) => {
                  const ocupado = ocupados.includes(h);
                  const activo = horaSel === h;
                  return (
                    <TouchableOpacity
                      key={h} disabled={ocupado}
                      style={[slot.base, activo && slot.on, ocupado && slot.off]}
                      onPress={() => setHoraSel(activo ? null : h)}
                    >
                      <Text style={[slot.txt, activo && { color: lp.white }, ocupado && { color: lp.textMuted }]}>{h}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <TouchableOpacity style={[reservar_btn, (guardando || !horaSel) && { opacity: 0.6 }]} onPress={reservar} disabled={guardando || !horaSel}>
                <Text style={{ color: lp.white, fontWeight: "800", fontSize: 15 }}>{guardando ? "Reservando..." : "Reservar"}</Text>
              </TouchableOpacity>
              <Text style={[ls.muted, { textAlign: "center", marginTop: 8, fontSize: 12 }]}>El pago se realizará más adelante.</Text>
            </>
          )}
        </>
      )}
    </ScrollView>
  );
}

const diaChip = {
  base: { paddingHorizontal: 14, paddingVertical: 9, borderRadius: 999, backgroundColor: lp.surface, borderWidth: 1, borderColor: lp.surfaceBorder, marginRight: 8 },
  on: { backgroundColor: lp.green, borderColor: lp.green },
  txt: { color: lp.textDark, fontWeight: "700", fontSize: 13 },
  txtOn: { color: lp.white },
};
const slot = {
  base: { paddingHorizontal: 20, paddingVertical: 12, borderRadius: 10, backgroundColor: "#D7E7DC", minWidth: 86, alignItems: "center" },
  on: { backgroundColor: lp.accent },
  off: { backgroundColor: "#ECEAE4" },
  txt: { color: lp.green, fontWeight: "800" },
};
const reservar_btn = { backgroundColor: lp.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 18 };
