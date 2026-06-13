// PRÓXIMOS PARTIDOS: calendario mensual con los días de partido marcados,
// y la lista de partidos debajo.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { fechaHora } from "../../format";
import { lp, ls } from "../../publicTheme";

const DIAS = ["L", "M", "M", "J", "V", "S", "D"];
const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

function claveDia(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function PlayerCalendarScreen() {
  const [partidos, setPartidos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [mes, setMes] = useState(() => { const h = new Date(); return new Date(h.getFullYear(), h.getMonth(), 1); });

  useFocusEffect(useCallback(() => {
    (async () => {
      try { setPartidos(await apiGet("/jugador/proximos-partidos")); }
      catch (_) { setPartidos([]); }
      finally { setCargando(false); }
    })();
  }, []));

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.green} style={{ marginTop: 40 }} /></View>;
  }

  const diasConPartido = new Set(
    partidos.filter((p) => p.fecha_hora).map((p) => claveDia(new Date(p.fecha_hora)))
  );

  // Construye la cuadrícula del mes mostrado
  const anio = mes.getFullYear();
  const m = mes.getMonth();
  const primerDia = new Date(anio, m, 1);
  // getDay(): 0=Dom..6=Sab -> queremos Lunes primero
  const offset = (primerDia.getDay() + 6) % 7;
  const totalDias = new Date(anio, m + 1, 0).getDate();
  const celdas = [];
  for (let i = 0; i < offset; i++) celdas.push(null);
  for (let d = 1; d <= totalDias; d++) celdas.push(d);

  function cambiarMes(delta) { setMes(new Date(anio, m + delta, 1)); }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Encabezado del mes */}
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <TouchableOpacity onPress={() => cambiarMes(-1)} style={nav.btn}><Text style={nav.txt}>‹</Text></TouchableOpacity>
        <Text style={{ color: lp.green, fontWeight: "800", fontSize: 16 }}>{MESES[m]} {anio}</Text>
        <TouchableOpacity onPress={() => cambiarMes(1)} style={nav.btn}><Text style={nav.txt}>›</Text></TouchableOpacity>
      </View>

      {/* Cabecera de días */}
      <View style={{ flexDirection: "row" }}>
        {DIAS.map((d, i) => (
          <Text key={i} style={{ flex: 1, textAlign: "center", color: lp.textMuted, fontWeight: "700", fontSize: 12 }}>{d}</Text>
        ))}
      </View>

      {/* Cuadrícula */}
      <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 6 }}>
        {celdas.map((d, i) => {
          const tiene = d != null && diasConPartido.has(claveDia(new Date(anio, m, d)));
          return (
            <View key={i} style={{ width: `${100 / 7}%`, aspectRatio: 1, alignItems: "center", justifyContent: "center" }}>
              {d != null && (
                <View style={[celda.dia, tiene && celda.diaConPartido]}>
                  <Text style={[celda.num, tiene && { color: lp.white, fontWeight: "800" }]}>{d}</Text>
                </View>
              )}
            </View>
          );
        })}
      </View>

      {/* Lista de partidos */}
      <Text style={[ls.sectionTitle, { marginTop: 18 }]}>Partidos</Text>
      {partidos.length === 0 ? (
        <Text style={ls.muted}>No tienes partidos programados.</Text>
      ) : (
        partidos.map((p) => (
          <View key={p.id} style={ls.row}>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>vs {p.rival || "?"}</Text>
              <Text style={ls.rowSub}>{fechaHora(p.fecha_hora)}{p.cancha_nombre ? ` · ${p.cancha_nombre}` : ""}</Text>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const nav = {
  btn: { width: 40, height: 40, borderRadius: 20, backgroundColor: lp.surface, borderWidth: 1, borderColor: lp.surfaceBorder, alignItems: "center", justifyContent: "center" },
  txt: { color: lp.green, fontSize: 22, fontWeight: "800" },
};
const celda = {
  dia: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center" },
  diaConPartido: { backgroundColor: lp.green },
  num: { color: lp.textDark, fontSize: 14 },
};
