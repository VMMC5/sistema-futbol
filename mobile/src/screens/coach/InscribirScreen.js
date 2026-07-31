// Inscripción de equipos a torneos: el entrenador elige uno de sus equipos, ve
// qué torneos admiten inscripción y paga la cuota cuando el torneo la exige.
// El servidor es la barrera real (409 por cierre/duplicado/cupo); esta pantalla
// solo pinta estados y evita viajes perdidos, no recalcula reglas.
import React, { useCallback, useMemo, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { lp, ls } from "../../publicTheme";

// Fecha local del dispositivo como cadena ISO (mismo truco de proximosDias()
// en ReservarScreen): new Date("YYYY-MM-DD") se interpreta como medianoche UTC
// y correría el cierre un día según la zona horaria.
function hoyISO() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// El día del cierre todavía se puede inscribir (el servidor rechaza con >);
// cerrado es a partir del día siguiente. Ante cualquier duda, manda el servidor.
function yaCerro(t) {
  return !!t.fecha_cierre_inscripciones && t.fecha_cierre_inscripciones < hoyISO();
}

function Etiqueta({ texto, fondo, color }) {
  return (
    <View style={{ backgroundColor: fondo, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 }}>
      <Text style={{ color, fontSize: 11, fontWeight: "800" }}>{texto}</Text>
    </View>
  );
}

export default function InscribirScreen({ navigation }) {
  const [equipos, setEquipos] = useState([]);
  const [torneos, setTorneos] = useState([]);
  const [inscripciones, setInscripciones] = useState([]);
  const [equipoSel, setEquipoSel] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [eqs, tns, ins] = await Promise.all([
        apiGet("/equipos"), apiGet("/torneos"), apiGet("/inscripciones"),
      ]);
      setEquipos(eqs);
      setTorneos(tns.filter((t) => t.estado !== "finalizado"));
      setInscripciones(ins);
      setEquipoSel((prev) => prev ?? (eqs.length ? eqs[0].id : null));
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo cargar");
    } finally {
      setCargando(false);
    }
  }, []);

  // Recarga al volver del pago: la inscripción pendiente ya aparece aceptada.
  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  // Inscripciones del equipo elegido, indexadas por torneo
  const delEquipo = useMemo(() => {
    const mapa = {};
    for (const i of inscripciones) if (i.equipo_id === equipoSel) mapa[i.torneo_id] = i;
    return mapa;
  }, [inscripciones, equipoSel]);

  const equipo = equipos.find((e) => e.id === equipoSel);

  async function inscribir(t) {
    setEnviando(true);
    try {
      const ins = await apiPost("/inscripciones", { torneo_id: t.id, equipo_id: equipoSel });
      if (ins.estado === "aceptada") {
        // Torneo sin cuota: el servidor la acepta directamente.
        Alert.alert("Inscripción aceptada", `${equipo?.nombre} quedó inscrito en ${t.nombre}.`);
        cargar();
      } else {
        // Con cuota nace pendiente: se confirma al completar el pago.
        navigation.navigate("Pago", {
          tipo: "inscripcion", id: ins.id,
          resumen: `Inscripción: ${equipo?.nombre} — ${t.nombre}`,
        });
      }
    } catch (e) {
      Alert.alert("No se pudo inscribir", e.message || "Inténtalo de nuevo");
    } finally {
      setEnviando(false);
    }
  }

  function pagar(i) {
    navigation.navigate("Pago", {
      tipo: "inscripcion", id: i.id,
      resumen: `Inscripción: ${i.equipo_nombre || equipo?.nombre || ""} — ${i.torneo_nombre || ""}`,
    });
  }

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.gold} style={{ marginTop: 40 }} /></View>;
  }

  if (!equipos.length) {
    return (
      <View style={ls.screen}>
        <Text style={[ls.muted, { margin: 20 }]}>No tienes equipos registrados. Crea tu equipo antes de inscribirlo a un torneo.</Text>
      </View>
    );
  }

  const misInscripciones = inscripciones.filter((i) => i.equipo_id === equipoSel);

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Selector de equipo */}
      {equipos.length > 1 && (
        <View style={ls.tabs}>
          {equipos.map((e) => (
            <TouchableOpacity key={e.id} style={[ls.tab, equipoSel === e.id && { backgroundColor: lp.gold }]} onPress={() => setEquipoSel(e.id)}>
              <Text style={[ls.tabText, equipoSel === e.id && { color: lp.goldText, fontWeight: "800" }]}>{e.nombre}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <Text style={ls.sectionTitle}>Torneos disponibles</Text>
      {torneos.length === 0 && <Text style={ls.muted}>No hay torneos abiertos por ahora.</Text>}
      {torneos.map((t) => {
        const ins = delEquipo[t.id];
        const cerrado = yaCerro(t);
        return (
          <View key={t.id} style={ls.row}>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{t.nombre}</Text>
              <Text style={ls.muted}>
                {t.cuota_inscripcion > 0 ? `Cuota: $${t.cuota_inscripcion}` : "Sin cuota"}
                {t.fecha_cierre_inscripciones ? ` · Cierra: ${t.fecha_cierre_inscripciones}` : ""}
              </Text>
            </View>
            {ins?.estado === "aceptada" ? (
              <Etiqueta texto="INSCRITO" fondo={lp.green} color={lp.white} />
            ) : ins?.estado === "pendiente" ? (
              <TouchableOpacity onPress={() => pagar(ins)} disabled={enviando}>
                <Etiqueta texto="PAGAR CUOTA" fondo={lp.maroon} color={lp.white} />
              </TouchableOpacity>
            ) : cerrado ? (
              <Etiqueta texto="CERRADO" fondo={lp.surfaceBorder} color={lp.textMuted} />
            ) : (
              <TouchableOpacity onPress={() => inscribir(t)} disabled={enviando}>
                <Etiqueta texto="INSCRIBIR" fondo={lp.gold} color={lp.goldText} />
              </TouchableOpacity>
            )}
          </View>
        );
      })}

      <Text style={ls.sectionTitle}>Mis inscripciones{equipo ? ` · ${equipo.nombre}` : ""}</Text>
      {misInscripciones.length === 0 && <Text style={ls.muted}>Este equipo no tiene inscripciones.</Text>}
      {misInscripciones.map((i) => (
        <View key={i.id} style={ls.row}>
          <Text style={[ls.rowTitle, { flex: 1 }]}>{i.torneo_nombre || `Torneo ${i.torneo_id}`}</Text>
          {i.estado === "aceptada"
            ? <Etiqueta texto="ACEPTADA" fondo={lp.green} color={lp.white} />
            : <TouchableOpacity onPress={() => pagar(i)} disabled={enviando}>
                <Etiqueta texto="PENDIENTE · PAGAR" fondo={lp.maroon} color={lp.white} />
              </TouchableOpacity>}
        </View>
      ))}
    </ScrollView>
  );
}
